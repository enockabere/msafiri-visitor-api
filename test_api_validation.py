#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# Test data from the actual request
test_data = {
    "title": "testing",
    "description": "<p>test</p>",
    "event_type": "Training",
    "status": "Draft",
    "start_date": "2026-01-01",
    "end_date": "2026-01-06",
    "vendor_accommodation_id": "1",
    "expected_participants": "20",
    "single_rooms": "20",
    "double_rooms": "22",
    "location": "The Heron Hotel, Jakaya Kikwete Rd, Nairobi, Kenya",
    "country": "",
    "latitude": -1.2891298,
    "longitude": 36.8069997,
    "banner_image": "",
    "duration_days": 5,
    "perdiem_rate": None,
    "perdiem_currency": "",
    "registration_deadline": "2025-12-25T12:06:00"
}

print("Testing EventUpdate schema validation through API...")
print(f"Test data: {json.dumps(test_data, indent=2, default=str)}")

try:
    response = requests.put(
        "http://localhost:8000/test-event-update",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("SUCCESS: EventUpdate validation passed through API!")
        print(f"Response: {response.json()}")
    else:
        print(f"FAILED: EventUpdate validation failed through API")
        print(f"Response text: {response.text}")
        
except Exception as e:
    print(f"ERROR: Failed to call API: {e}")