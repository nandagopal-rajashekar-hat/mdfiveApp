import os
import time
import requests
from flask import Blueprint, request, jsonify, send_file

download_api = Blueprint('download_api', __name__)

LOGIN_URL = "https://qa-api.systemisers.in/users/sign_in"
REPORT_URL_TEMPLATE = "https://qa-api.systemisers.in/api/v1/report_generator/{report_id}/generation?type=project_report"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def download_report(report_id, email, password, retries=3, delay=5):
    session = requests.Session()
    print("Logging in...")

    payload = {
            "email": email,
            "password": password
    }
    try:
        response = session.post(LOGIN_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Login failed: {e}")
        if e.response is not None:
            print("Response text:", e.response.text)
        return None

    print("Logged in successfully!")
    report_url = REPORT_URL_TEMPLATE.format(report_id=report_id)

    os.makedirs("output_reports", exist_ok=True)
    output_file = f"output_reports/Report_{report_id}.pdf"

    for attempt in range(1, retries + 1):
        try:
            print(f"Attempting to download report (Attempt {attempt})...")
            report_response = session.get(report_url)

            if report_response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(report_response.content)
                print(f"Report saved as: {output_file}")
                return output_file
            else:
                print(f"⚠️ Attempt {attempt}: Status {report_response.status_code}. Retrying in {delay}s...")
                time.sleep(delay)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            time.sleep(delay)

    print(f"Failed to download report {report_id} after {retries} attempts.")
    return None


@download_api.route("/api/download-report", methods=["POST"])
def download_report_api():
    data = request.get_json()
    report_id = data.get("report_id")

    if not report_id:
        return jsonify({"status": "error", "message": "Missing report_id"}), 400

    print(f"=== Downloading Report ===\nDownloading report ID: {report_id}")
    email = "bharath@gmail.com"
    password = "Testing@12345"

    output_file = download_report(report_id, email, password)

    if not output_file:
        return jsonify({"status": "error", "message": f"Failed to download report {report_id}"}), 500

    return send_file(
        output_file,
        as_attachment=True,
        download_name=os.path.basename(output_file),  
        mimetype="application/pdf" 
    )
