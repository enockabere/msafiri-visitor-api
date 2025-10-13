#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.schemas.accommodation import VendorAccommodationCreate

# Test creating a vendor accommodation with the fields the frontend sends
test_data = {
    "vendor_name": "Test Hotel",
    "location": "Test Location",
    "latitude": "1.234567",
    "longitude": "36.789012",
    "accommodation_type": "Hotel",
    "single_rooms": 10,
    "double_rooms": 5,
    "description": "Test description"
}

try:
    vendor_create = VendorAccommodationCreate(**test_data)
    print("Schema validation successful!")
    print(f"Vendor data: {vendor_create.dict()}")
except Exception as e:
    print(f"Schema validation failed: {e}")