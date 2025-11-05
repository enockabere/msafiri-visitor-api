#!/usr/bin/env python3
"""
Script to send passport data to the MSF HR API
"""

import requests
import json
from datetime import datetime

# API Configuration
API_URL = "https://ko-hr.kenya.msf.org/api/v1/update-passport-data/1857"
API_KEY = "n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW"

# Headers
headers = {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY
}

# Payload data
payload = {
    "passport_no": "600000001",
    "given_names": "JANE     KKKKKKKKKKKKKKKKKKKK",
    "surname": "SPECIMEN",
    "issue_country": "ZAF",
    "date_of_birth": "1980-01-01",
    "date_of_expiry": "2019-03-29",
    "date_of_issue": "2006-11-04",
    "gender": "F",
    "nationality": "South Africa",
    "user_email": "kenya-visitor@oca.msf.org",
    "location_id": {
        "name": "Test Event 0001",
        "training": "Lake Naivasha Simba Lodge, Moi South Lake Road, Naivasha, Kenya",
        "accommodation": "Lake Naivasha Simba Lodge",
        "country": "Kenya",
        "city": "Naivasha",
        "from_date": "2025-12-01",
        "to_date": "2025-12-12"
    },
    "confirmed": True
}

def send_passport_data():
    """Send passport data to the API using PATCH method"""
    
    print("=" * 80)
    print("📤 SENDING PASSPORT DATA TO API")
    print("=" * 80)
    print(f"\n🔗 URL: {API_URL}")
    print(f"\n📋 METHOD: PATCH")
    
    print(f"\n📤 HEADERS:")
    print(json.dumps({k: v if k != 'x-api-key' else v[:10] + '...' for k, v in headers.items()}, indent=2))
    
    print(f"\n📤 PAYLOAD:")
    print(json.dumps(payload, indent=2))
    
    try:
        # Send PATCH request
        response = requests.patch(
            API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print("\n" + "=" * 80)
        print("📥 API RESPONSE")
        print("=" * 80)
        print(f"\n📊 Status Code: {response.status_code}")
        print(f"\n📋 Response Headers:")
        print(json.dumps(dict(response.headers), indent=2))
        
        print(f"\n📥 Response Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            print(response.text)
        
        # Check response status
        if response.status_code == 200:
            print("\n✅ SUCCESS: Request completed")
        else:
            print(f"\n⚠️  WARNING: Unexpected status code {response.status_code}")
            
        return response
        
    except requests.exceptions.RequestException as e:
        print("\n" + "=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print(f"\n{type(e).__name__}: {str(e)}")
        return None

if __name__ == "__main__":
    print("\n🚀 Starting Passport Data Update Script")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    response = send_passport_data()
    
    print("\n" + "=" * 80)
    print("🏁 SCRIPT COMPLETE")
    print("=" * 80)