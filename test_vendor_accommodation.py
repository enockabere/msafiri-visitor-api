#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.guesthouse import VendorAccommodation
from app.schemas.accommodation import VendorAccommodationCreate
from app.crud.accommodation import vendor_accommodation

def test_vendor_accommodation_creation():
    """Test creating a vendor accommodation"""
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create test vendor accommodation
        vendor_data = VendorAccommodationCreate(
            vendor_name="Test Hotel",
            accommodation_type="Hotel",
            location="Naivasha",
            contact_person="Test Person",
            contact_phone="0877727287",
            contact_email="test@example.com",
            capacity=10,
            description="Test hotel description"
        )
        
        # Create with tenant_id = 2 (as in the error log)
        vendor = vendor_accommodation.create_with_tenant(
            db=db, 
            obj_in=vendor_data, 
            tenant_id=2
        )
        
        print(f"Successfully created vendor accommodation:")
        print(f"ID: {vendor.id}")
        print(f"Name: {vendor.vendor_name}")
        print(f"Type: {vendor.accommodation_type}")
        print(f"Location: {vendor.location}")
        print(f"Capacity: {vendor.capacity}")
        print(f"Created at: {vendor.created_at}")
        
        return True
        
    except Exception as e:
        print(f"Error creating vendor accommodation: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing vendor accommodation creation...")
    success = test_vendor_accommodation_creation()
    
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed!")
        sys.exit(1)