from flask import Flask
from flask_cors import CORS
from flask import Flask, request, jsonify
from logic.insert_enhancement import insert_od_cc_enhancement_details
from routes import register_routes
import traceback
from logic.fetch_json import fetch_json_from_db
from logic.insert_report import insert_report
from db_utils.db_utils import select_all, select_one, insert_data, update_data
from logic.report_downloader import download_report
from flask import send_file
import re
from datetime import datetime
import threading
import time
import zipfile
import os
import tempfile

app = Flask(__name__)
CORS(app)

register_routes(app)

def extract_report_number(report_name):
    match = re.match(r"Report_(\d+)", report_name)
    return match.group(1) if match else None
bulk_processing_status = {}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Flask API is running',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/test', methods=['GET'])
def get_valid_report():
    """Get valid reports with sample IDs and counts"""
    try:
        query = """
        SELECT 
            SUBSTRING(report_name FROM 'Report_([0-9]+)') as sample_report_id,
            COUNT(*) as report_count
        FROM test_suite.json_report_test_data_app
        WHERE report_name ~ 'Report_[0-9]+'
        GROUP BY SUBSTRING(report_name FROM 'Report_([0-9]+)')
        ORDER BY sample_report_id::INTEGER DESC
        """
        
        reports = select_all(query)
        
        formatted_reports = []
        for report in reports:
            formatted_reports.append({
                'sample_report_id': report[0],
                'report_count': report[1]
            })
        
        return jsonify({
            'status': 'success',
            'data': formatted_reports,
            'message': f'Found {len(formatted_reports)} report groups'
        }), 200
        
    except Exception as e:
        print(f"Error in get_valid_report: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500

def log_report_processing(report_name, status, report_id=None, error_message=None):
    """Log report processing to database"""
    try:
        now = datetime.now()
        query = """
        INSERT INTO test_suite.report_processing_log 
        (original_report_name, inserted_report_id, status, error_message, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        values = (report_name, report_id, status, error_message, now, now)
        log_id = insert_data(query, values)
        print(f"Logged report processing: {report_name} -> {status} (Log ID: {log_id})")
    except Exception as e:
        print(f"Failed to log report processing: {e}")

@app.route('/api/process-single-report', methods=['POST'])
def process_single_report():
    """Process a single report by name"""
    try:
        print("=== Processing Single Report ===")
        
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
        
        report_name = data.get('report_name')
        print(f"Report name: {report_name}")
        
        if not report_name:
            return jsonify({
                'status': 'error',
                'message': 'Report name is required'
            }), 400
        user_id = 187
        org_id = 179
        company_id = 179
        
        print(f"Fetching data for report: {report_name}")
        json_data = fetch_json_from_db(report_name)
        if not json_data:
            log_report_processing(report_name, 'failed', error_message='No data found')
            return jsonify({
                'status': 'error',
                'message': f'No data found for report: {report_name}'
            }), 404
        
        print("Data fetched successfully, inserting report...")
        report_id = insert_report(json_data, user_id, org_id, company_id)
        
        log_report_processing(report_name, 'success', report_id)
        print(f"Report inserted with ID: {report_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'Report {report_name} processed successfully',
            'data': {
                'report_name': report_name,
                'report_id': report_id
            }
        }), 200
        
    except Exception as e:
        log_report_processing(report_name if 'report_name' in locals() else 'unknown', 'failed', error_message=str(e))
        print(f"Error in process_single_report: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def process_report_async(report_name, user_id, org_id, company_id, batch_id):
    """Process a single report asynchronously"""
    try:
        print(f"Processing report: {report_name}")
        json_data = fetch_json_from_db(report_name)
        if not json_data:
            log_report_processing(report_name, 'failed', error_message='No data found')
            return {'report_name': report_name, 'status': 'failed', 'error': 'No data found'}
        
        report_id = insert_report(json_data, user_id, org_id, company_id)
        
        log_report_processing(report_name, 'success', report_id)
        print(f"Successfully processed report: {report_name} -> {report_id}")
        
        return {
            'report_name': report_name,
            'status': 'success',
            'report_id': report_id
        }
        
    except Exception as e:
        error_message = str(e)
        log_report_processing(report_name, 'failed', error_message=error_message)
        print(f"Failed to process report {report_name}: {e}")
        
        return {
            'report_name': report_name,
            'status': 'failed',
            'error': error_message
        }

def bulk_process_reports_worker(report_names, batch_id):
    """Worker function for bulk processing reports"""
    global bulk_processing_status
    
    user_id = 187
    org_id = 179
    company_id = 179
    
    total_reports = len(report_names)
    processed = 0
    results = []
    
    bulk_processing_status[batch_id] = {
        'status': 'processing',
        'total': total_reports,
        'processed': 0,
        'results': []
    }
    
    for report_name in report_names:
        try:
            result = process_report_async(report_name, user_id, org_id, company_id, batch_id)
            results.append(result)
            processed += 1
            
            bulk_processing_status[batch_id].update({
                'processed': processed,
                'results': results
            })
            
            print(f"Progress: {processed}/{total_reports} reports processed")
            
        except Exception as e:
            print(f"Error processing report {report_name}: {e}")
            results.append({
                'report_name': report_name,
                'status': 'failed',
                'error': str(e)
            })
            processed += 1
            
            bulk_processing_status[batch_id].update({
                'processed': processed,
                'results': results
            })
    
    bulk_processing_status[batch_id]['status'] = 'completed'
    print(f"Bulk processing completed for batch {batch_id}")

@app.route('/api/process-bulk-reports', methods=['POST'])
def process_bulk_reports():
    """Process multiple reports in bulk"""
    try:
        print("=== Processing Bulk Reports ===")
        
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
        
        report_names = data.get('report_names', [])
        if not report_names or not isinstance(report_names, list):
            return jsonify({
                'status': 'error',
                'message': 'report_names must be a non-empty list'
            }), 400
        
        if len(report_names) > 50:
            return jsonify({
                'status': 'error',
                'message': 'Maximum 50 reports allowed per batch'
            }), 400
        
        clean_report_names = [name.strip() for name in report_names if name.strip()]
        if not clean_report_names:
            return jsonify({
                'status': 'error',
                'message': 'No valid report names provided'
            }), 400
        
        batch_id = f"batch_{int(time.time())}_{len(clean_report_names)}"
        
        thread = threading.Thread(
            target=bulk_process_reports_worker,
            args=(clean_report_names, batch_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Bulk processing started for {len(clean_report_names)} reports',
            'data': {
                'batch_id': batch_id,
                'total_reports': len(clean_report_names),
                'report_names': clean_report_names
            }
        }), 200
        
    except Exception as e:
        print(f"Error in process_bulk_reports: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/bulk-status/<batch_id>', methods=['GET'])
def get_bulk_status(batch_id):
    """Get the status of bulk processing"""
    global bulk_processing_status
    
    if batch_id not in bulk_processing_status:
        return jsonify({
            'status': 'error',
            'message': 'Batch ID not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': bulk_processing_status[batch_id]
    }), 200

@app.route('/api/report-mappings', methods=['GET'])
def get_report_mappings():
    """Get all report processing mappings"""
    try:
        query = """
        SELECT 
            id,
            original_report_name,
            inserted_report_id,
            status,
            error_message,
            created_at
        FROM test_suite.report_processing_log
        ORDER BY created_at DESC
        LIMIT 100
        """

        mappings = select_all(query)
        
        formatted_mappings = []
        for mapping in mappings:
            formatted_mappings.append({
                'id': mapping[0],
                'original_report_name': mapping[1],
                'inserted_report_id': mapping[2],
                'status': mapping[3],
                'error_message': mapping[4],
                'created_at': mapping[5].isoformat() if mapping[5] else None
            })
        
        return jsonify({
            'status': 'success',
            'data': formatted_mappings,
            'message': f'Found {len(formatted_mappings)} report mappings'
        }), 200
        
    except Exception as e:
        print(f"Error in get_report_mappings: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500

@app.route("/api/download-report", methods=["POST"])
def download_report_api():
    data = request.get_json()
    report_id = data.get("report_id")

    if not report_id:
        return jsonify({"status": "error", "message": "Missing report_id"}), 400

    print(f"Downloading report ID: {report_id}")
    email = "bharath@gmail.com"
    password = "Testing@12345"

    output_file = download_report(report_id, email, password)
    if not output_file:
        return jsonify({"status": "error", "message": f"Failed to download report {report_id}"}), 500

    return send_file(output_file, as_attachment=True)

@app.route("/api/download-bulk-reports", methods=["POST"])
def download_bulk_reports_api():
    """Download multiple reports as a ZIP file"""
    try:
        data = request.get_json()
        report_ids = data.get("report_ids", [])
        email = data.get("email")
        password = data.get("password")

        if not report_ids or not isinstance(report_ids, list):
            return jsonify({"status": "error", "message": "Missing or invalid report_ids"}), 400

        if len(report_ids) > 50:  
            return jsonify({"status": "error", "message": "Maximum 50 reports allowed for bulk download"}), 400

        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password are required"}), 400

        print(f"Bulk downloading {len(report_ids)} reports")

        temp_dir = tempfile.mkdtemp()
        downloaded_files = []
        failed_downloads = []

        try:
            for report_id in report_ids:
                try:
                    print(f"Downloading report ID: {report_id}")
                    output_file = download_report(report_id, email, password)
                    
                    if output_file and os.path.exists(output_file):
                        
                        filename = f"Report_{report_id}.pdf"
                        temp_file_path = os.path.join(temp_dir, filename)
                        
                    
                        with open(output_file, 'rb') as src, open(temp_file_path, 'wb') as dst:
                            dst.write(src.read())
                        
                        downloaded_files.append((temp_file_path, filename))
                        print(f"Successfully downloaded report {report_id}")
                         
                        try:
                            os.remove(output_file)
                        except:
                            pass
                    else:
                        failed_downloads.append(report_id)
                        print(f"Failed to download report {report_id}")
                        
                except Exception as e:
                    print(f"Error downloading report {report_id}: {e}")
                    failed_downloads.append(report_id)

            if not downloaded_files:
                return jsonify({
                    "status": "error", 
                    "message": "No reports could be downloaded"
                }), 500

            zip_filename = f"BulkReports_{int(time.time())}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path, filename in downloaded_files:
                    zipf.write(file_path, filename)
            
            print(f"Created ZIP file with {len(downloaded_files)} reports")
            
            if failed_downloads:
                print(f"⚠️ Failed to download {len(failed_downloads)} reports: {failed_downloads}")
            def remove_temp_files():
                """Clean up temp files after response"""
                try:
                    for file_path, _ in downloaded_files:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    os.rmdir(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp files: {e}")

            response = send_file(
                zip_path, 
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
            import atexit
            atexit.register(remove_temp_files)
            
            return response

        except Exception as e:
            print(f"Error creating ZIP file: {e}")
            return jsonify({
                "status": "error", 
                "message": f"Failed to create ZIP file: {str(e)}"
            }), 500

    except Exception as e:
        print(f"Error in download_bulk_reports_api: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/reports', methods=['GET'])
def get_all_reports():
    """Get all processed reports"""
    try:
        query = """
        SELECT 
            pr.id,
            pr.created_at,
            pr.is_fresh_term_loan,
            pr.is_od_enhancement,
            pr.is_takeover,
            pr.is_od_renewal,
            pr.is_od_fresh,
            b.name as bank_name,
            ls.name as loan_scheme_name
        FROM systemisers.project_reports pr
        LEFT JOIN systemisers.banks b ON pr.bank_id = b.id
        LEFT JOIN systemisers.loan_schemes ls ON pr.loan_scheme_id = ls.id
        ORDER BY pr.created_at DESC
        LIMIT 50
        """
        
        reports = select_all(query)
        
        formatted_reports = []
        for report in reports:
            formatted_reports.append({
                'id': report[0],
                'created_at': report[1].isoformat() if report[1] else None,
                'is_fresh_term_loan': report[2],
                'is_od_enhancement': report[3],
                'is_takeover': report[4],
                'is_od_renewal': report[5],
                'is_od_fresh': report[6],
                'bank_name': report[7],
                'loan_scheme_name': report[8]
            })
        
        return jsonify({
            'status': 'success',
            'data': formatted_reports,
            'message': f'Found {len(formatted_reports)} reports'
        }), 200
        
    except Exception as e:
        print(f"Error in get_all_reports: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500
@app.route('/api/process-all-reports', methods=['POST'])
def process_all_reports():
    try:
        user_id = 187
        org_id = 179
        company_id = 179 

        query = """
        SELECT DISTINCT report_name
        FROM test_suite.json_report_test_data
        ORDER BY report_name DESC
        LIMIT 50
        """
        report_names = select_all(query)  
        
        processed = []
        failed = []

        for (report_name,) in report_names:
            try:
                json_data = fetch_json_from_db(report_name)
                if not json_data:
                    failed.append({'report_name': report_name, 'error': 'No data found'})
                    log_report_processing(report_name, 'failed', error_message='No data found')
                    continue
                
                report_id = insert_report(json_data, user_id, org_id, company_id)
                org_id = insert_od_cc_enhancement_details(json_data, org_id, company_id, report_id, user_id)
                processed.append({'report_name': report_name, 'report_id': report_id})
                log_report_processing(report_name, 'success', report_id)
            except Exception as e:
                failed.append({'report_name': report_name, 'error': str(e)})
                log_report_processing(report_name, 'failed', error_message=str(e))

        return jsonify({
            'status': 'success',
            'message': f'Processed {len(processed)} reports with {len(failed)} failures',
            'data': {
                'processed': processed,
                'failed': failed
            }
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/reportSummary', methods=['GET'])
def get_report_summary():
    """Get report combination summary"""
    try:
        query = """
        SELECT 
            CASE 
                WHEN pr.is_fresh_term_loan AND pr.is_od_enhancement AND pr.is_takeover THEN 'Fresh + OD Enhancement + Takeover'
                WHEN pr.is_fresh_term_loan AND pr.is_od_enhancement THEN 'Fresh + OD Enhancement'
                WHEN pr.is_fresh_term_loan AND pr.is_takeover THEN 'Fresh + Takeover'
                WHEN pr.is_od_enhancement AND pr.is_takeover THEN 'OD Enhancement + Takeover'
                WHEN pr.is_fresh_term_loan THEN 'Fresh Term Loan'
                WHEN pr.is_od_enhancement THEN 'OD Enhancement'
                WHEN pr.is_takeover THEN 'Takeover'
                WHEN pr.is_od_renewal THEN 'OD Renewal'
                WHEN pr.is_od_fresh THEN 'Fresh OD'
                ELSE 'Other'
            END as report_combination,
            COUNT(*) as report_count
        FROM systemisers.project_reports pr
        GROUP BY 
            CASE 
                WHEN pr.is_fresh_term_loan AND pr.is_od_enhancement AND pr.is_takeover THEN 'Fresh + OD Enhancement + Takeover'
                WHEN pr.is_fresh_term_loan AND pr.is_od_enhancement THEN 'Fresh + OD Enhancement'
                WHEN pr.is_fresh_term_loan AND pr.is_takeover THEN 'Fresh + Takeover'
                WHEN pr.is_od_enhancement AND pr.is_takeover THEN 'OD Enhancement + Takeover'
                WHEN pr.is_fresh_term_loan THEN 'Fresh Term Loan'
                WHEN pr.is_od_enhancement THEN 'OD Enhancement'
                WHEN pr.is_takeover THEN 'Takeover'
                WHEN pr.is_od_renewal THEN 'OD Renewal'
                WHEN pr.is_od_fresh THEN 'Fresh OD'
                ELSE 'Other'
            END
        ORDER BY report_count DESC
        """
        
        summary_data = select_all(query)
        
        formatted_summary = []
        for row in summary_data:
            formatted_summary.append({
                'report_combination': row[0],
                'report_count': row[1]
            })
        
        return jsonify({
            'status': 'success',
            'data': formatted_summary,
            'message': f'Found {len(formatted_summary)} report combinations'
        }), 200
        
    except Exception as e:
        print(f"Error in get_report_summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': []
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
