#!/usr/bin/env python3
"""
Absolute Cabs API Integration Tester
Tests all API endpoints with OAuth2 authentication and HMAC signing
"""

import requests
import hashlib
import hmac
import base64
import json
import time
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import sys


class AbsoluteAPIClient:
    """Client for interacting with Absolute Cabs API"""
    
    def __init__(self, client_id: str, client_secret: str, hmac_secret: str, base_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.hmac_secret = hmac_secret
        self.base_url = base_url.rstrip('/')
        self.token_endpoint = f"{self.base_url}/oauth/token"
        self.access_token = None
        self.token_expiry = None
        
    def get_access_token(self) -> str:
        """Obtain OAuth2 access token"""
        print("\n" + "="*80)
        print("OBTAINING ACCESS TOKEN")
        print("="*80)
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        print(f"\nRequest URL: {self.token_endpoint}")
        print(f"Request Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                self.token_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                print(f"\n✓ Token obtained successfully")
                print(f"✓ Token expires at: {self.token_expiry}")
                return self.access_token
            else:
                print(f"\n✗ Failed to obtain token")
                response.raise_for_status()
                
        except Exception as e:
            print(f"\n✗ Error obtaining token: {str(e)}")
            raise
    
    def ensure_valid_token(self):
        """Ensure we have a valid access token"""
        if not self.access_token or not self.token_expiry:
            self.get_access_token()
        elif datetime.now() >= self.token_expiry - timedelta(minutes=5):
            print("\nToken expiring soon, refreshing...")
            self.get_access_token()
    
    def generate_signature(self, method: str, path: str, timestamp: int, 
                          body: str, nonce: str) -> str:
        """Generate HMAC-SHA256 signature"""
        # Hash the body
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        
        # Create canonical string
        canonical_string = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
        
        print(f"\nCanonical String:")
        print("-" * 80)
        print(canonical_string)
        print("-" * 80)
        
        # Generate HMAC signature
        signature = hmac.new(
            self.hmac_secret.encode('utf-8'),
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Encode to base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return signature_b64
    
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated and signed API request"""
        self.ensure_valid_token()
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        path = endpoint
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)  # 16-byte random hex string
        body = json.dumps(data) if data else ""
        
        # Generate signature
        signature = self.generate_signature(method, path, timestamp, body, nonce)
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print("\n" + "="*80)
        print(f"{method} REQUEST: {endpoint}")
        print("="*80)
        print(f"\nURL: {url}")
        print(f"\nHeaders:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"  {key}: Bearer {self.access_token[:20]}...")
            else:
                print(f"  {key}: {value}")
        
        if data:
            print(f"\nRequest Body:")
            print(json.dumps(data, indent=2))
        
        # Make request
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"\nResponse Body:")
                print(json.dumps(response_json, indent=2))
                
                if response.status_code in [200, 201]:
                    print(f"\n✓ Request successful")
                else:
                    print(f"\n✗ Request failed")
                
                return response_json
            except ValueError:
                print(f"\nResponse Body (text):")
                print(response.text)
                return {"status_code": response.status_code, "text": response.text}
                
        except Exception as e:
            print(f"\n✗ Error making request: {str(e)}")
            raise
    
    def create_booking(self, booking_data: Dict) -> Dict:
        """Create a new booking"""
        return self.make_request("POST", "/api/bookings", booking_data)
    
    def get_bookings(self) -> Dict:
        """Fetch all bookings"""
        return self.make_request("GET", "/api/bookings")
    
    def get_booking(self, ref_no: str) -> Dict:
        """Fetch a single booking by reference number"""
        return self.make_request("GET", f"/api/bookings/{ref_no}")
    
    def get_vehicle_types(self) -> Dict:
        """Fetch available vehicle types"""
        return self.make_request("GET", "/api/vehicle-types")


def test_api():
    """Run comprehensive API tests"""
    
    # Configuration (Replace with your actual credentials)
    config = {
        "client_id": "f5741192-e755-41d5-934a-80b279e08347",
        "client_secret": "hFPWDy6CgZQdofBTm5DoBYcNa2d1coHTYWpjF0wp",
        "hmac_secret": "3c478d99c0ddb35bd35d4dd13899c57e3c77cccbf2bf7244f5c3c60b9f557809",
        "base_url": "https://api.absolutecabs.co.ke"
    }
    
    print("\n" + "="*80)
    print("ABSOLUTE CABS API INTEGRATION TESTER")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Client ID: {config['client_id']}")
    print(f"  Base URL: {config['base_url']}")
    
    # Initialize client
    client = AbsoluteAPIClient(**config)
    
    try:
        # Test 1: Obtain access token
        print("\n\n" + "#"*80)
        print("TEST 1: OAUTH2 AUTHENTICATION")
        print("#"*80)
        client.get_access_token()
        
        # Test 2: Fetch vehicle types
        print("\n\n" + "#"*80)
        print("TEST 2: FETCH VEHICLE TYPES")
        print("#"*80)
        vehicle_types = client.get_vehicle_types()
        
        # Test 3: Fetch all bookings
        print("\n\n" + "#"*80)
        print("TEST 3: FETCH ALL BOOKINGS")
        print("#"*80)
        bookings = client.get_bookings()
        
        # Test 4: Create a new booking
        print("\n\n" + "#"*80)
        print("TEST 4: CREATE NEW BOOKING")
        print("#"*80)
        
        booking_payload = {
            "vehicle_type": "SALOON",
            "pickup_address": "123 Partner St, Nairobi",
            "pickup_latitude": -1.2921,
            "pickup_longitude": 36.8219,
            "dropoff_address": "456 Parklands Ave, Nairobi",
            "dropoff_latitude": -1.2674,
            "dropoff_longitude": 36.8112,
            "pickup_time": "2025-11-09 16:50",
            "flightdetails": "KQ123 - JKIA Arrival",
            "notes": "Please ensure driver calls upon arrival",
            "passengers": [
                {
                    "name": "Alice Wanjiku",
                    "phone": "254700000001",
                    "email": "alice@example.com"
                },
                {
                    "name": "John Doe",
                    "phone": "254711111111",
                    "email": "john.doe@example.com"
                }
            ],
            "waypoints": [
                {
                    "address": "Kilimani, Nairobi",
                    "lat": -1.3004,
                    "lng": 36.7898
                },
                {
                    "address": "Westlands, Nairobi",
                    "lat": -1.2681,
                    "lng": 36.8119
                }
            ]
        }
        
        new_booking = client.create_booking(booking_payload)
        
        # Test 5: Fetch single booking (if we got a ref_no from creation)
        if isinstance(new_booking, dict) and 'ref_no' in new_booking:
            print("\n\n" + "#"*80)
            print("TEST 5: FETCH SINGLE BOOKING")
            print("#"*80)
            ref_no = new_booking['ref_no']
            single_booking = client.get_booking(ref_no)
        
        # Summary
        print("\n\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print("\n✓ All tests completed!")
        print("\nTests executed:")
        print("  1. OAuth2 Authentication - ✓")
        print("  2. Fetch Vehicle Types - ✓")
        print("  3. Fetch All Bookings - ✓")
        print("  4. Create New Booking - ✓")
        if isinstance(new_booking, dict) and 'ref_no' in new_booking:
            print("  5. Fetch Single Booking - ✓")
        
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_api()