#!/usr/bin/env python3
"""
Fetch Absolute Cabs Booking by Reference Number
Usage: python fetch_booking_by_ref.py <ref_no>
Example: python fetch_booking_by_ref.py BK11-34716-2BF4
"""

import requests
import hashlib
import hmac
import base64
import json
import time
import secrets
import sys

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


def fetch_booking(ref_no, verbose=False):
    """Fetch booking by reference number"""
    
    # Get token
    if verbose:
        print(f"🔑 Obtaining access token...")
    token = get_access_token()
    if verbose:
        print(f"✓ Token obtained\n")
    
    # Prepare request
    path = f"/api/bookings/{ref_no}"
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    body = ""
    
    # Generate signature
    signature = generate_signature("GET", path, timestamp, body, nonce)
    
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
    
    if verbose:
        print(f"📡 Fetching booking: {ref_no}")
        print(f"   URL: {BASE_URL}{path}\n")
    
    response = requests.get(f"{BASE_URL}{path}", headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch booking: {response.status_code} - {response.text}")
    
    return response.json()


def display_booking(booking_data):
    """Display booking details in a formatted way"""
    
    # Handle different response structures
    if 'data' in booking_data:
        booking = booking_data['data']
    elif 'booking' in booking_data:
        booking = booking_data['booking']
    else:
        booking = booking_data
    
    print("="*80)
    print("📋 BOOKING DETAILS")
    print("="*80)
    
    # Basic Info
    print(f"\n🔖 Reference Number: {booking.get('ref_no')}")
    print(f"🆔 Booking ID: {booking.get('id')}")
    print(f"📅 Date: {booking.get('pickup_date')}")
    print(f"⏰ Time: {booking.get('pickup_time')}")
    print(f"🚗 Vehicle: {booking.get('vehicle_type')}")
    print(f"📊 Status: {booking.get('status') or 'Pending'}")
    
    # Locations
    print(f"\n📍 PICKUP:")
    print(f"   {booking.get('pickup_address')}")
    print(f"   📍 Coordinates: ({booking.get('pickup_latitude')}, {booking.get('pickup_longitude')})")
    
    print(f"\n📍 DROPOFF:")
    print(f"   {booking.get('dropoff_address')}")
    print(f"   📍 Coordinates: ({booking.get('dropoff_latitude')}, {booking.get('dropoff_longitude')})")
    
    # Additional Info
    if booking.get('flightdetails'):
        print(f"\n✈️  Flight: {booking.get('flightdetails')}")
    
    if booking.get('notes'):
        print(f"📝 Notes: {booking.get('notes')}")
    
    # Passengers
    passengers = booking.get('passengers', [])
    if passengers:
        print(f"\n👥 PASSENGERS ({len(passengers)}):")
        for i, passenger in enumerate(passengers, 1):
            print(f"   {i}. {passenger.get('name')}")
            print(f"      📞 {passenger.get('telephone')}")
            print(f"      📧 {passenger.get('email')}")
    
    # Assignment Status
    drivers = booking.get('drivers', [])
    vehicles = booking.get('vehicles', [])
    waypoints = booking.get('waypoints', [])
    
    print(f"\n🚕 ASSIGNMENT STATUS:")
    print(f"   Drivers: {len(drivers)} assigned")
    if drivers:
        for driver in drivers:
            print(f"      - {driver}")
    
    print(f"   Vehicles: {len(vehicles)} assigned")
    if vehicles:
        for vehicle in vehicles:
            print(f"      - {vehicle}")
    
    if waypoints:
        print(f"\n📍 WAYPOINTS ({len(waypoints)}):")
        for i, wp in enumerate(waypoints, 1):
            print(f"   {i}. {wp.get('address')}")
            if wp.get('lat') and wp.get('lng'):
                print(f"      ({wp.get('lat')}, {wp.get('lng')})")
    
    print("\n" + "="*80)


def main():
    """Main function"""
    
    # Get ref_no from command line or use default
    if len(sys.argv) > 1:
        ref_no = sys.argv[1]
    else:
        # Your most recent booking
        ref_no = "BK11-34716-2BF4"
        print(f"No ref_no provided, using: {ref_no}")
        print(f"Usage: python {sys.argv[0]} <ref_no>\n")
    
    try:
        # Fetch booking
        print(f"Fetching booking {ref_no}...\n")
        booking_data = fetch_booking(ref_no, verbose=True)
        
        # Display formatted output
        display_booking(booking_data)
        
        # Also show raw JSON
        print("\n📄 RAW JSON RESPONSE:")
        print("="*80)
        print(json.dumps(booking_data, indent=2))
        print("="*80)
        
        print("\n✅ SUCCESS - Booking fetched successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()