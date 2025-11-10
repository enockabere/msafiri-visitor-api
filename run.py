#!/usr/bin/env python3
"""
MSF Passport Data Fetching Script
Fetches passport details using passport ID
"""

import requests
import json


def fetch_passport_data(passport_id):
    """Fetch passport data using passport ID"""
    
    API_URL = f"https://ko-hr.kenya.msf.org/api/v1/get-passport-data/{passport_id}"
    API_KEY = "n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW"
    
    print(f"Fetching passport data for ID: {passport_id}")
    print(f"API Endpoint: {API_URL}")
    
    # Headers with API key
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # JSON payload with passport_id
    payload = {
        "passport_id": passport_id
    }
    
    try:
        # Send GET request with JSON payload
        response = requests.get(API_URL, json=payload, headers=headers, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ SUCCESS!")
            print("\n" + "="*60)
            print("PASSPORT DETAILS")
            print("="*60)
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"\n✗ FAILED")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ REQUEST FAILED")
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    passport_id = 1886
    
    result = fetch_passport_data(passport_id)
    
    if result:
        print("\n" + "="*60)
        print("Data retrieved successfully!")
        print("="*60)
    else:
        print("\nFailed to retrieve passport data")