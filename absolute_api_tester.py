#!/usr/bin/env python3
"""
Test Pooled Booking for Absolute Cabs
Tests the exact payload that's failing in your logs with fixes
"""

import requests
import hashlib
import hmac
import base64
import json
import time
import secrets

# Configuration
CLIENT_ID = "f5741192-e755-41d5-934a-80b279e08347"
CLIENT_SECRET = "hFPWDy6CgZQdofBTm5DoBYcNa2d1coHTYWpjF0wp"
HMAC_SECRET = "3c478d99c0ddb35bd35d4dd13899c57e3c77cccbf2bf7244f5c3c60b9f557809"
BASE_URL = "https://api.absolutecabs.co.ke"


def get_access_token():
    """Get OAuth2 access token"""
    response = requests.post(
        f"{BASE_URL}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    )
    if response.status_code != 200:
        raise Exception(f"Failed to get token: {response.text}")
    return response.json()["access_token"]


def generate_signature(method, path, timestamp, body, nonce):
    """Generate HMAC-SHA256 signature"""
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
    signature = hmac.new(
        HMAC_SECRET.encode(),
        canonical.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()


def create_pooled_booking(payload):
    """Create a pooled booking"""
    
    # Get token
    print("🔑 Obtaining access token...")
    token = get_access_token()
    print("✓ Token obtained\n")
    
    # Prepare request
    path = "/api/bookings"
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    body = json.dumps(payload)
    
    # Generate signature
    signature = generate_signature("POST", path, timestamp, body, nonce)
    
    # Make request
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Client-Id": CLIENT_ID,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print("📡 Creating pooled booking...")
    print(f"URL: {BASE_URL}{path}\n")
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print("\n" + "="*80)
    
    response = requests.post(f"{BASE_URL}{path}", headers=headers, json=payload)
    
    return response


def main():
    """Main function to test pooled bookings"""
    
    print("="*80)
    print("🚕 ABSOLUTE CABS POOLED BOOKING TEST")
    print("="*80)
    print("\nTesting pooled booking for 2 passengers")
    print("Route: JKIA → Swiss-Belinn Nairobi")
    print("="*80)
    
    # Test 1: Your original failing payload (with empty phone numbers)
    print("\n\n" + "#"*80)
    print("TEST 1: ORIGINAL PAYLOAD (Will Fail - Empty Phone)")
    print("#"*80)
    
    original_payload = {
        "vehicle_type": "Rav4",
        "pickup_address": "JKIA (NBO), Embakasi, Nairobi, Kenya",
        "pickup_latitude": -1.3192,
        "pickup_longitude": 36.9278,
        "dropoff_address": "Swiss-Belinn Nairobi, Kandara Road, Nairobi, Kenya",
        "dropoff_latitude": -1.2921,
        "dropoff_longitude": 36.8219,
        "pickup_time": "2025-11-12 19:06",
        "flightdetails": "KLM 744u48; TESY 7577",
        "notes": "Pooled booking for 2 passengers. Pooled booking from admin portal",
        "passengers": [
            {
                "name": "Leonard Kiprop",
                "phone": "",  # ❌ EMPTY - This causes the 422 error
                "email": "leonard.kiprop@oca.msf.org"
            },
            {
                "name": "kenya-visitor-msf-oca",
                "phone": "",  # ❌ EMPTY - This causes the 422 error
                "email": "kenya-visitor@oca.msf.org"
            }
        ],
        "waypoints": []
    }
    
    response1 = create_pooled_booking(original_payload)
    
    print(f"Response Status: {response1.status_code}")
    try:
        response_data = response1.json()
        print(f"Response Body:")
        print(json.dumps(response_data, indent=2))
        
        if response1.status_code == 422:
            print("\n❌ FAILED - As expected (empty phone numbers)")
            print("\n🔍 Validation Errors:")
            if 'errors' in response_data:
                print(json.dumps(response_data['errors'], indent=2))
    except:
        print(response1.text)
    
    # Test 2: Fixed payload with valid phone numbers
    print("\n\n" + "#"*80)
    print("TEST 2: FIXED PAYLOAD (With Valid Phone Numbers)")
    print("#"*80)
    
    fixed_payload = {
        "vehicle_type": "Rav4",
        "pickup_address": "JKIA (NBO), Embakasi, Nairobi, Kenya",
        "pickup_latitude": -1.3192,
        "pickup_longitude": 36.9278,
        "dropoff_address": "Swiss-Belinn Nairobi, Kandara Road, Nairobi, Kenya",
        "dropoff_latitude": -1.2921,
        "dropoff_longitude": 36.8219,
        "pickup_time": "2025-11-12 19:06",
        "flightdetails": "KLM 744u48; TESY 7577",
        "notes": "Pooled booking for 2 passengers. Pooled booking from admin portal",
        "passengers": [
            {
                "name": "Leonard Kiprop",
                "phone": "254712345678",  # ✅ VALID PHONE
                "email": "leonard.kiprop@oca.msf.org"
            },
            {
                "name": "kenya-visitor-msf-oca",
                "phone": "254712345679",  # ✅ VALID PHONE
                "email": "kenya-visitor@oca.msf.org"
            }
        ],
        "waypoints": []
    }
    
    response2 = create_pooled_booking(fixed_payload)
    
    print(f"Response Status: {response2.status_code}")
    try:
        response_data = response2.json()
        print(f"Response Body:")
        print(json.dumps(response_data, indent=2))
        
        if response2.status_code in [200, 201]:
            print("\n✅ SUCCESS - Pooled booking created!")
            
            # Extract booking details
            if 'booking' in response_data:
                booking = response_data['booking']
                print(f"\n📋 Booking Details:")
                print(f"   Ref No: {booking.get('ref_no')}")
                print(f"   ID: {booking.get('id')}")
                print(f"   Vehicle: {booking.get('vehicle_type')}")
                print(f"   Passengers: {len(booking.get('passengers', []))}")
                print(f"   Pickup: {booking.get('pickup_time')}")
        else:
            print("\n❌ FAILED")
            if 'errors' in response_data:
                print("\n🔍 Validation Errors:")
                print(json.dumps(response_data['errors'], indent=2))
    except:
        print(response2.text)
    
    # Test 3: Alternative - Use placeholder phone if actual phones not available
    print("\n\n" + "#"*80)
    print("TEST 3: ALTERNATIVE - Placeholder Phone Numbers")
    print("#"*80)
    
    placeholder_payload = {
        "vehicle_type": "Rav4",
        "pickup_address": "JKIA (NBO), Embakasi, Nairobi, Kenya",
        "pickup_latitude": -1.3192,
        "pickup_longitude": 36.9278,
        "dropoff_address": "Swiss-Belinn Nairobi, Kandara Road, Nairobi, Kenya",
        "dropoff_latitude": -1.2921,
        "dropoff_longitude": 36.8219,
        "pickup_time": "2025-11-12 19:06",
        "flightdetails": "KLM 744u48; TESY 7577",
        "notes": "Pooled booking for 2 passengers. Pooled booking from admin portal",
        "passengers": [
            {
                "name": "Leonard Kiprop",
                "phone": "254700000001",  # Placeholder format
                "email": "leonard.kiprop@oca.msf.org"
            },
            {
                "name": "kenya-visitor-msf-oca",
                "phone": "254700000002",  # Placeholder format
                "email": "kenya-visitor@oca.msf.org"
            }
        ],
        "waypoints": []
    }
    
    response3 = create_pooled_booking(placeholder_payload)
    
    print(f"Response Status: {response3.status_code}")
    try:
        response_data = response3.json()
        print(f"Response Body:")
        print(json.dumps(response_data, indent=2))
        
        if response3.status_code in [200, 201]:
            print("\n✅ SUCCESS - Booking created with placeholder phones!")
        else:
            print("\n❌ FAILED")
            if 'errors' in response_data:
                print("\n🔍 Validation Errors:")
                print(json.dumps(response_data['errors'], indent=2))
    except:
        print(response3.text)
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print("\n1. Original Payload (Empty Phones): ❌ Expected to fail")
    print("2. Fixed Payload (Valid Phones): ✅ Should succeed")
    print("3. Placeholder Phones: ⚠️ Alternative option")
    print("\n💡 FIX: Always provide valid phone numbers for all passengers!")
    print("   - Cannot be empty strings")
    print("   - Must be in format: 254XXXXXXXXX (12 digits)")
    print("   - Use real numbers or placeholder numbers like 254700000001")
    print("="*80)


if __name__ == "__main__":
    main()