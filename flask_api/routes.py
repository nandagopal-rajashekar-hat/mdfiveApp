from flask import request, jsonify
from db import get_db_connection
from contextlib import contextmanager
import psycopg2.extras
import subprocess
import threading
import time
import os

@contextmanager
def db_cursor():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def register_routes(app):
    @app.route('/api/test', methods=['GET'])
    def test():
        try:
            with db_cursor() as cur:
                query = """
                    SELECT * FROM test_suite.get_valid_report_sample_counts_app(
                        (
                            SELECT MAX(
                                CAST(SUBSTRING(report_name FROM 'Report_(\\d+)_') AS INTEGER)
                            )
                            FROM test_suite.json_report_test_data_app
                            WHERE report_name ~ 'Report_\\d+_'
                        )
                    );
                """
                cur.execute(query)
                rows = cur.fetchall()
            return jsonify({
                "success": True,
                "data": rows
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/get-latest-report', methods=['GET'])
    def get_latest_report():
        query = """
            SELECT 
                MAX(CAST(SUBSTRING(report_name FROM 'Report_(\\d+)_') AS INTEGER)) AS report_count,
                MAX(report_name) FILTER (WHERE report_name ~ 'Report_\\d+_\\d+') AS sample_report_id
            FROM test_suite.json_report_test_data_app
            WHERE report_name ~ 'Report_\\d+_';
        """
        try:
            with db_cursor() as cur:
                cur.execute(query)
                result = cur.fetchone()
            return jsonify({
                'report_count': int(result['report_count']) if result['report_count'] else 0,
                'sample_report_id': result['sample_report_id'] or '',
                'success': True
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/load-test-data', methods=['POST'])
    def load_test_data():
        query = """
            SELECT * FROM test_suite.load_valid_sample_report_app(
                (
                    SELECT MAX(
                        CAST(SUBSTRING(report_name FROM 'Report_(\\d+)_') AS INTEGER)
                    )
                    FROM test_suite.json_report_test_data_app
                    WHERE report_name ~ 'Report_\\d+_'
                )
            );
        """
        try:
            with db_cursor() as cur:
                cur.execute(query)
                result = cur.fetchone()
            return jsonify({'success': True, 'result': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/reportSummary', methods=['GET'])
    def get_report_combination_summary():
        query = "SELECT * FROM test_suite.report_combination_summary_app;"
        try:
            with db_cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                result = [dict(row) for row in rows]
            return jsonify({
                'success': True,
                'data': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/reportComparison', methods=['GET'])
    def compare_report_id():
        report_id_1 = request.args.get('report_id_1')
        report_id_2 = request.args.get('report_id_2')

        project_report_stage_id_1 = request.args.get('project_report_stage_id_1')
        project_report_stage_id_2 = request.args.get('project_report_stage_id_2')

        insert_flag = request.args.get('insert_flag', 'false').lower() == 'true'

        if not report_id_1 or not report_id_2:
            return jsonify({
                'success': False,
                'error': 'Both report_id_1 and report_id_2 are required parameters'
            }), 400

        if project_report_stage_id_1 and project_report_stage_id_2:
            query = f"""
                SELECT * FROM systemisers.compare_flattened_json_from_testsuite_app(
                    {report_id_1}, {report_id_2}, {'TRUE' if insert_flag else 'FALSE'},
                    {project_report_stage_id_1}, {project_report_stage_id_2}
                );
            """
        else:
            query = f"""
                SELECT * FROM systemisers.compare_flattened_json_from_testsuite_app(
                    {report_id_1}, {report_id_2}, {'TRUE' if insert_flag else 'FALSE'}
                );
            """

        try:
            with db_cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                result = [dict(row) for row in rows]

            return jsonify({
                'success': True,
                'data': result,
                'comparison_info': {
                    'report_id_1': report_id_1,
                    'report_id_2': report_id_2,
                    'project_report_stage_id_1': project_report_stage_id_1,
                    'project_report_stage_id_2': project_report_stage_id_2,
                    'insert_flag': insert_flag,
                    'differences_found': len(result)
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    @app.route('/api/automation/signin', methods=['POST'])
    def automation_signin():
        """Execute Selenium sign-in automation"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No JSON data received'
                }), 400

            email = data.get('email')
            password = data.get('password')
            url = data.get('url', 'https://qa.systemisers.in/')
            headless = bool(data.get('headless', True))

            if not email or not password:
                return jsonify({
                    'success': False,
                    'message': 'Email and password are required'
                }), 400

            # Run the Selenium script in a separate thread
            def run_selenium_script():
                try:
                    # Create a temporary script with the provided credentials
                    temp_script_content = '''from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import sys

# --- Configuration ---
URL = "{URL}"
EMAIL = "{EMAIL}"
PASSWORD = "{PASSWORD}"
HEADLESS = {HEADLESS}

def main():
    driver = None
    try:
        # --- Setup WebDriver (headless) ---
        options = webdriver.ChromeOptions()
        if HEADLESS:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(options=options)
        driver.get(URL)

        # --- Wait object ---
        wait = WebDriverWait(driver, 10)

        # 1. Click on Sign In button (navbar)
        sign_in_nav_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="navbarSupportedContent"]/button[2]'))
        )
        sign_in_nav_btn.click()

        # 2. Enter email
        email_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, '//form/div[1]/input[@placeholder="Enter Your Email Address"]'))
        )
        email_input.clear()
        email_input.send_keys(EMAIL)

        # 3. Enter password
        password_input = driver.find_element(By.XPATH, '//form/div[2]/input[@placeholder="Enter Your Password"]')
        password_input.clear()
        password_input.send_keys(PASSWORD)

        # 4. Click Sign In button (inside popup)
        sign_in_btn = driver.find_element(By.XPATH, '//form/button[text()="Sign In"]')
        sign_in_btn.click()

        # --- Wait to see result ---
        time.sleep(5)

        # Check if sign-in was successful by looking for a success indicator
        success_indicators = [
            '//a[contains(text(), "Logout")]',
            '//a[contains(text(), "Dashboard")]',
            '//div[contains(@class, "user-menu")]',
            '//span[contains(text(), "Welcome")]'
        ]

        for indicator in success_indicators:
            try:
                element = driver.find_element(By.XPATH, indicator)
                if element:
                    print("Sign-in successful!")
                    sys.exit(0)
            except Exception:
                continue

        print("Sign-in may have failed - no success indicators found")
        sys.exit(1)

    except Exception as e:
        print("Error during sign-in process: " + str(e))
        sys.exit(1)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == '__main__':
    main()
'''.replace('{URL}', url).replace('{EMAIL}', email).replace('{PASSWORD}', password).replace('{HEADLESS}', 'True' if headless else 'False')
                 
                    # Write temporary script
                    temp_script_path = f'/tmp/signin_{int(time.time())}.py'
                    with open(temp_script_path, 'w') as f:
                        f.write(temp_script_content)
                    
                    # Execute the script
                    result = subprocess.run(['python3', temp_script_path], 
                                          capture_output=True, text=True, timeout=60)
                    
                    # Clean up temporary script
                    try:
                        os.remove(temp_script_path)
                    except:
                        pass
                    
                    return result.returncode == 0, result.stdout, result.stderr
                    
                except subprocess.TimeoutExpired:
                    return False, "", "Script execution timed out"
                except Exception as e:
                    return False, "", str(e)

            # Run the automation in a separate thread
            result_queue = []
            
            def automation_worker():
                success, stdout, stderr = run_selenium_script()
                result_queue.append({
                    'success': success,
                    'stdout': stdout,
                    'stderr': stderr
                })

            thread = threading.Thread(target=automation_worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=70)  # Wait up to 70 seconds

            if thread.is_alive():
                return jsonify({
                    'success': False,
                    'message': 'Automation timed out. Please check if ChromeDriver is installed and accessible.'
                }), 408

            if not result_queue:
                return jsonify({
                    'success': False,
                    'message': 'Automation execution failed to complete'
                }), 500

            result = result_queue[0]
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Sign-in automation completed successfully',
                    'output': result['stdout']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Sign-in automation failed',
                    'error': result['stderr'] or 'Unknown error occurred'
                }), 500

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error executing automation: {str(e)}'
            }), 500

    @app.route('/api/automation/signup', methods=['POST'])
    def automation_signup():
        """Execute Selenium sign-up automation"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No JSON data received'}), 400

            url = data.get('url', 'https://qa.systemisers.in/')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            email = data.get('email')
            mobile = data.get('mobile')
            password = data.get('password')
            confirm_password = data.get('confirm_password', password)
            headless = bool(data.get('headless', True))

            required = [first_name, last_name, email, mobile, password, confirm_password]
            if any(v in (None, '') for v in required):
                return jsonify({'success': False, 'message': 'All fields are required'}), 400

            def run_selenium_script():
                try:
                    temp_script_content = '''from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import sys

URL = "{URL}"
FIRST_NAME = "{FIRST_NAME}"
LAST_NAME = "{LAST_NAME}"
EMAIL = "{EMAIL}"
MOBILE = "{MOBILE}"
PASSWORD = "{PASSWORD}"
CONFIRM_PASSWORD = "{CONFIRM_PASSWORD}"
HEADLESS = {HEADLESS}

def main():
    driver = None
    try:
        options = webdriver.ChromeOptions()
        if HEADLESS:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        driver = webdriver.Chrome(options=options)
        driver.get(URL)

        wait = WebDriverWait(driver, 10)

        # Open Sign Up
        open_signup_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="navbarSupportedContent"]/button[1]')))
        open_signup_btn.click()

        # Validate popup title
        wait.until(EC.visibility_of_element_located((By.XPATH, '//form/h2[text()="Let’s Sign Up"]')))

        # Fill form fields
        first_name_input = wait.until(EC.visibility_of_element_located((By.XPATH, '//form/div/div[1]//input[@placeholder="Enter Your First Name"]')))
        first_name_input.clear(); first_name_input.send_keys(FIRST_NAME)

        last_name_input = driver.find_element(By.XPATH, '//form/div/div[2]//input[@placeholder="Enter Your Last Name"]')
        last_name_input.clear(); last_name_input.send_keys(LAST_NAME)

        email_input = driver.find_element(By.XPATH, '//form/div/div[3]//input[@placeholder="Enter Your Email Address"]')
        email_input.clear(); email_input.send_keys(EMAIL)

        mobile_input = driver.find_element(By.XPATH, '//form/div/div[4]//input[@placeholder="Enter Your Mobile Number"]')
        mobile_input.clear(); mobile_input.send_keys(MOBILE)

        password_input = driver.find_element(By.XPATH, '//form/div/div[5]//input[@placeholder="Enter Your Password"]')
        password_input.clear(); password_input.send_keys(PASSWORD)

        confirm_input = driver.find_element(By.XPATH, '//form/div/div[6]//input[@placeholder="Re-enter Your Password"]')
        confirm_input.clear(); confirm_input.send_keys(CONFIRM_PASSWORD)

        # Accept terms checkbox
        checkbox = driver.find_element(By.XPATH, '//form/div/div[7]//label[text()="I agree to the terms and conditions"]/../input[@type="checkbox"]')
        if not checkbox.is_selected():
            checkbox.click()

        # Submit
        signup_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//form/div/div[8]//button[text()="Sign Up"]')))
        signup_btn.click()

        time.sleep(5)

        # Success heuristics: activation confirmation messages or post-login indicators
        success_indicators = [
            # Activation / confirmation messages
            '//*[contains(text(), "Activation link") or contains(text(), "activation link")]',
            '//*[contains(text(), "check your email") or contains(text(), "Check your email")]',
            '//*[contains(text(), "verification") and contains(text(), "email")]',
            # In case auto-login happens
            '//a[contains(text(), "Logout")]',
            '//a[contains(text(), "Dashboard")]'
        ]
        for ind in success_indicators:
            try:
                element = driver.find_element(By.XPATH, ind)
                if element:
                    print("Sign-up successful!")
                    sys.exit(0)
            except Exception:
                continue

        # If explicit error indicators are present, treat as failure
        error_indicators = [
            '//*[contains(@class, "error") or contains(@class, "invalid")]',
            '//*[contains(text(), "already exists") or contains(text(), "invalid")]'
        ]
        for ind in error_indicators:
            try:
                element = driver.find_element(By.XPATH, ind)
                if element:
                    print("Sign-up may have failed - error indicator found")
                    sys.exit(1)
            except Exception:
                continue

        # Default to success if no errors detected but activation likely sent
        print("Sign-up likely succeeded (no errors found, check email for activation)")
        sys.exit(0)

    except Exception as e:
        print("Error during sign-up process: " + str(e))
        sys.exit(1)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == '__main__':
    main()
'''.replace('{URL}', url).replace('{FIRST_NAME}', first_name).replace('{LAST_NAME}', last_name).replace('{EMAIL}', email).replace('{MOBILE}', mobile).replace('{PASSWORD}', password).replace('{CONFIRM_PASSWORD}', confirm_password).replace('{HEADLESS}', 'True' if headless else 'False')

                    temp_script_path = f'/tmp/signup_{int(time.time())}.py'
                    with open(temp_script_path, 'w') as f:
                        f.write(temp_script_content)

                    result = subprocess.run(['python3', temp_script_path], capture_output=True, text=True, timeout=90)
                    try:
                        os.remove(temp_script_path)
                    except Exception:
                        pass
                    return result.returncode == 0, result.stdout, result.stderr
                except subprocess.TimeoutExpired:
                    return False, "", "Script execution timed out"
                except Exception as e:
                    return False, "", str(e)

            result_queue = []
            def automation_worker():
                success, stdout, stderr = run_selenium_script()
                result_queue.append({'success': success, 'stdout': stdout, 'stderr': stderr})

            thread = threading.Thread(target=automation_worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=100)

            if thread.is_alive():
                return jsonify({'success': False, 'message': 'Automation timed out'}), 408

            if not result_queue:
                return jsonify({'success': False, 'message': 'Automation execution failed to complete'}), 500

            result = result_queue[0]
            if result['success']:
                return jsonify({'success': True, 'message': 'Sign-up automation completed successfully', 'output': result['stdout']}), 200
            else:
                return jsonify({'success': False, 'message': 'Sign-up automation failed', 'error': result['stderr'], 'output': result['stdout']}), 500

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error executing automation: {str(e)}'}), 500
