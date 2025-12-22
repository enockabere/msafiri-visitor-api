#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test script to validate EventUpdate schema with the exact request data
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas.event import EventUpdate
import json

# Exact data from the request logs
request_data = {
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
    "registration_deadline": "2025-12-24T10:04:00"
}

print("Testing EventUpdate validation with exact request data...")
print(f"Request data: {json.dumps(request_data, indent=2, default=str)}")

try:
    print("Creating EventUpdate object...")
    event_update = EventUpdate(**request_data)
    print("SUCCESS: EventUpdate validation passed!")
    print(f"Created object: {event_update}")
    print(f"Object dict: {event_update.dict()}")
except Exception as e:
    print(f"FAILED: EventUpdate validation failed")
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")