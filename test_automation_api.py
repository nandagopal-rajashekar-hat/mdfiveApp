#!/usr/bin/env python3
"""
Test script for the automation API endpoint
"""
import requests
import json

def test_automation_api():
    """Test the automation sign-in API endpoint"""
    
    # Test data
    test_data = {
        "email": "lalitha@gmail.com",
        "password": "Testing@12345",
        "url": "https://qa.systemisers.in/"
    }
    
    # API endpoint
    url = "http://127.0.0.1:5000/api/automation/signin"
    
    try:
        print("Testing automation API endpoint...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")
        
        # Make the request
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask server is running on port 5000")
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request took too long")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_automation_api()
