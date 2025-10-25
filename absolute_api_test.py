#!/usr/bin/env python3
"""
Absolute Cabs API - Simple Booking Script
Creates cab bookings using OAuth2 and HMAC signatures
"""

import requests
import hmac
import hashlib
import base64
import time
import secrets
import json
from datetime import datetime, timedelta


class AbsoluteCabsAPI:
    """Simple client for Absolute Cabs booking API"""
    
    def __init__(self):
        # API Configuration
        self.client_id = "f5741192-e755-41d5-934a-80b279e08347"
        self.client_secret = "hFPWDy6CgZQdofBTm5DoBYcNa2d1coHTYWpjF0wp"
        self.hmac_secret = "3c478d99c0ddb35bd35d4dd13899c57e3c77cccbf2bf7244f5c3c60b9f557809"
        self.token_url = "https://api.absolutecabs.co.ke/oauth/token"
        self.base_url = "https://api.absolutecabs.co.ke"
        
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self):
        """Get OAuth2 access token with wildcard scope"""
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "*"  # Wildcard scope - gives full access
        }
        
        response = requests.post(self.token_url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access_token']
        expires_in = data.get('expires_in', 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        
        print(f"✓ Authenticated successfully")
        return True
    
    def _ensure_authenticated(self):
        """Make sure we have a valid token"""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.get_access_token()
    
    def _generate_signature(self, method, path, body, timestamp, nonce):
        """Generate HMAC-SHA256 signature"""
        # Hash the request body
        if body:
            body_hash = hashlib.sha256(json.dumps(body).encode()).hexdigest()
        else:
            body_hash = hashlib.sha256(b'').hexdigest()
        
        # Create canonical string (exact format required by API)
        canonical_string = f"{method}\n{path}\n{timestamp}\n{body_hash}\n{nonce}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.hmac_secret.encode(),
            canonical_string.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def create_booking(self, pickup_address, pickup_lat, pickup_lng,
                      dropoff_address, dropoff_lat, dropoff_lng,
                      pickup_datetime, passenger_name, passenger_phone,
                      passenger_email="", vehicle_type="Sedan",
                      flight_details="", notes=""):
        """
        Create a cab booking
        
        Args:
            pickup_address: Pickup location address
            pickup_lat: Pickup latitude
            pickup_lng: Pickup longitude
            dropoff_address: Drop-off location address
            dropoff_lat: Drop-off latitude
            dropoff_lng: Drop-off longitude
            pickup_datetime: Pickup time (format: "2025-10-24T14:00:00")
            passenger_name: Passenger name
            passenger_phone: Phone (format: "254700000001")
            passenger_email: Email (optional)
            vehicle_type: Vehicle type (Sedan, SUV, etc.)
            flight_details: Flight number (optional)
            notes: Additional notes (optional)
        
        Returns:
            Booking details including reference number
        """

        self._ensure_authenticated()
        
        booking_data = {
            "pickup_address": pickup_address,
            "pickup_latitude": pickup_lat,
            "pickup_longitude": pickup_lng,
            "dropoff_address": dropoff_address,
            "dropoff_latitude": dropoff_lat,
            "dropoff_longitude": dropoff_lng,
            "pickup_time": pickup_datetime,
            "passenger_name": passenger_name,
            "passenger_phone": passenger_phone,
            "passenger_email": passenger_email,
            "vehicle_type": vehicle_type,
            "flightdetails": flight_details,
            "notes": notes
        }
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._generate_signature("POST", "/api/bookings", booking_data, timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
        
        # Send request
        url = f"{self.base_url}/api/bookings"
        response = requests.post(url, json=booking_data, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_bookings(self):
        """Get all bookings"""
        self._ensure_authenticated()
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._generate_signature("GET", "/api/bookings", None, timestamp, nonce)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Client-Id": self.client_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }
        
        url = f"{self.base_url}/api/bookings"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Absolute Cabs Booking Test")
    print("=" * 60)
    
    # Initialize API
    api = AbsoluteCabsAPI()
    
    # Create a booking
    print("\nCreating booking...")
    try:
        result = api.create_booking(
            pickup_address="JKIA Airport",
            pickup_lat=-1.319167,
            pickup_lng=36.927778,
            dropoff_address="Westlands, Nairobi",
            dropoff_lat=-1.268333,
            dropoff_lng=36.808611,
            pickup_datetime="2025-10-25T15:00:00",
            passenger_name="John Doe",
            passenger_phone="254712345678",
            passenger_email="john@example.com",
            vehicle_type="SUV",
            flight_details="KQ101",
            notes="Please wait at arrivals gate"
        )
        
        print("\n✓ Booking created successfully!")
        print(f"\nBooking Reference: {result['booking']['ref_no']}")
        print(f"Passenger: {result['booking']['passenger_name']}")
        print(f"Phone: {result['booking']['telephone']}")
        print(f"From: {result['booking']['travelfrom']}")
        print(f"To: {result['booking']['travelto']}")
        print(f"Pickup: {result['booking']['pickup_date']} {result['booking']['pickup_time']}")
        print(f"Vehicle: {result['booking']['vehicle_type_name']}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")