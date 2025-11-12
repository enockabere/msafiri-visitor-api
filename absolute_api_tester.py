#!/usr/bin/env python3
"""
Quick test with CORRECT vehicle type
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

# Get access token
response = requests.post(
    f"{BASE_URL}/oauth/token",
    json={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
)
token = response.json()["access_token"]

# Prepare booking with CORRECT vehicle type
booking = {
    "vehicle_type": "Rav4",  # ✅ CHANGED FROM "SUV"
    "pickup_address": "Swiss-Belinn Nairobi, Kandara Road, Nairobi, Kenya",
    "pickup_latitude": -1.2921,
    "pickup_longitude": 36.8219,
    "dropoff_address": "Jomo Kenyatta International Airport (NBO), Embakasi, Nairobi, Kenya",
    "dropoff_latitude": -1.3192,
    "dropoff_longitude": 36.9278,
    "pickup_time": "2025-11-14 17:10",
    "flightdetails": "KLM 37484",
    "notes": "MSF Event Transport",
    "passengers": [
        {
            "name": "Leonard Kiprop",
            "phone": "254712345678",  # ✅ Fixed phone
            "email": "leonard.kiprop@oca.msf.org"
        }
    ],
    "waypoints": []
}

# Prepare signature
path = "/api/bookings"
timestamp = int(time.time())
nonce = secrets.token_hex(16)
body = json.dumps(booking)
body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
canonical = f"POST\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
signature = base64.b64encode(
    hmac.new(HMAC_SECRET.encode(), canonical.encode(), hashlib.sha256).digest()
).decode()

# Make request
headers = {
    "Authorization": f"Bearer {token}",
    "X-Client-Id": CLIENT_ID,
    "X-Timestamp": str(timestamp),
    "X-Nonce": nonce,
    "X-Signature": signature,
    "Content-Type": "application/json"
}

print("Creating booking with vehicle_type='Rav4'...")
response = requests.post(f"{BASE_URL}{path}", headers=headers, json=booking)

print(f"\nStatus: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

if response.status_code in [200, 201]:
    print("\n✅ SUCCESS! Booking created!")
else:
    print("\n❌ Failed - see error above")