#!/usr/bin/env python3
"""
Test script for Absolute Cabs integration
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TENANT_SLUG = "msf-ea"

def test_vehicle_types():
    """Test fetching vehicle types"""
    print("Testing vehicle types endpoint...")
    
    # First get tenant ID
    tenant_response = requests.get(f"{BASE_URL}/tenants/slug/{TENANT_SLUG}")
    if tenant_response.status_code != 200:
        print(f"Failed to get tenant: {tenant_response.status_code}")
        return
    
    tenant_id = tenant_response.json()["id"]
    
    # Get vehicle types
    response = requests.get(f"{BASE_URL}/transport-requests/tenant/{tenant_id}/vehicle-types")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Vehicle types fetched successfully: {len(data['vehicle_types'])} types")
        for vehicle in data['vehicle_types']:
            print(f"  - {vehicle['type']}: {vehicle['seats']} seats")
    else:
        print(f"✗ Failed to fetch vehicle types: {response.status_code}")
        print(response.text)

def test_pooling_suggestions():
    """Test pooling suggestions endpoint"""
    print("\nTesting pooling suggestions endpoint...")
    
    # First get tenant ID
    tenant_response = requests.get(f"{BASE_URL}/tenants/slug/{TENANT_SLUG}")
    if tenant_response.status_code != 200:
        print(f"Failed to get tenant: {tenant_response.status_code}")
        return
    
    tenant_id = tenant_response.json()["id"]
    
    # Get pooling suggestions
    response = requests.get(f"{BASE_URL}/transport-requests/tenant/{tenant_id}/pooling-suggestions")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Pooling suggestions fetched successfully: {len(data['suggestions'])} suggestions")
        for suggestion in data['suggestions']:
            print(f"  - Group {suggestion['group_id']}: {suggestion['passenger_count']} passengers, {suggestion['suggested_vehicle']}")
    else:
        print(f"✗ Failed to fetch pooling suggestions: {response.status_code}")
        print(response.text)

def test_transport_requests():
    """Test fetching transport requests"""
    print("\nTesting transport requests endpoint...")
    
    # First get tenant ID
    tenant_response = requests.get(f"{BASE_URL}/tenants/slug/{TENANT_SLUG}")
    if tenant_response.status_code != 200:
        print(f"Failed to get tenant: {tenant_response.status_code}")
        return
    
    tenant_id = tenant_response.json()["id"]
    
    # Get transport requests
    response = requests.get(f"{BASE_URL}/transport-requests/tenant/{tenant_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Transport requests fetched successfully: {len(data)} requests")
        for request in data[:3]:  # Show first 3
            print(f"  - {request['passenger_name']}: {request['pickup_address']} → {request['dropoff_address']} ({request['status']})")
    else:
        print(f"✗ Failed to fetch transport requests: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("Testing Absolute Cabs Integration")
    print("=" * 50)
    
    test_vehicle_types()
    test_pooling_suggestions()
    test_transport_requests()
    
    print("\n" + "=" * 50)
    print("Test completed!")