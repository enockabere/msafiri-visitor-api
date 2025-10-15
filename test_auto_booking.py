#!/usr/bin/env python3
"""
Test script to check auto booking functionality
"""
import requests
import json

# Configuration
API_BASE = "http://localhost:8000/api/v1"
# You'll need to get a valid token from login
TOKEN = "your_token_here"

def test_auto_booking():
    """Test the auto booking endpoint"""
    
    # Test data - replace with actual IDs from your database
    event_id = 1  # Replace with actual event ID
    participant_id = 1  # Replace with actual participant ID
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "X-Tenant-ID": "msf"  # Replace with your tenant
    }
    
    # Test the auto booking endpoint
    url = f"{API_BASE}/auto-booking/events/{event_id}/auto-book-participant"
    data = {
        "participant_id": participant_id
    }
    
    print(f"🧪 Testing auto booking endpoint: {url}")
    print(f"📊 Data: {data}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"📈 Response status: {response.status_code}")
        print(f"📋 Response body: {response.text}")
        
        if response.ok:
            result = response.json()
            print(f"✅ Auto booking successful: {result}")
        else:
            print(f"❌ Auto booking failed: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Error: {e}")

def check_allocations():
    """Check current allocations"""
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Tenant-ID": "msf"
    }
    
    url = f"{API_BASE}/accommodation/allocations"
    
    print(f"🔍 Checking allocations: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"📈 Response status: {response.status_code}")
        
        if response.ok:
            allocations = response.json()
            print(f"📊 Found {len(allocations)} allocations:")
            for allocation in allocations:
                print(f"  - {allocation.get('guest_name')} ({allocation.get('accommodation_type')})")
        else:
            print(f"❌ Failed to fetch allocations: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    print("🚀 Auto Booking Test Script")
    print("=" * 50)
    
    print("\n1. Checking current allocations...")
    check_allocations()
    
    print("\n2. Testing auto booking...")
    # test_auto_booking()  # Uncomment when you have valid token and IDs
    
    print("\n✅ Test complete")