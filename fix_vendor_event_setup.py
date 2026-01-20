#!/usr/bin/env python3
"""
Fix missing vendor event accommodation setup for event 18
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import Event
from app.models.guesthouse import VendorEventAccommodation

def fix_vendor_event_setup():
    """Create missing vendor event accommodation setup for event 18"""
    db = next(get_db())
    
    try:
        # Get event 18
        event = db.query(Event).filter(Event.id == 18).first()
        if not event:
            print("❌ Event 18 not found")
            return
        
        print(f"📊 Event 18 details:")
        print(f"  Title: {event.title}")
        print(f"  Vendor ID: {event.vendor_accommodation_id}")
        print(f"  Single Rooms: {event.single_rooms}")
        print(f"  Double Rooms: {event.double_rooms}")
        print(f"  Tenant ID: {event.tenant_id}")
        
        if not event.vendor_accommodation_id:
            print("❌ Event has no vendor accommodation assigned")
            return
        
        if event.single_rooms is None or event.double_rooms is None:
            print("❌ Event has no room configuration")
            return
        
        # Check if vendor event setup already exists
        existing_setup = db.query(VendorEventAccommodation).filter(
            VendorEventAccommodation.event_id == 18,
            VendorEventAccommodation.vendor_accommodation_id == event.vendor_accommodation_id
        ).first()
        
        if existing_setup:
            print(f"✅ Vendor event setup already exists with ID: {existing_setup.id}")
            print(f"  Single Rooms: {existing_setup.single_rooms}")
            print(f"  Double Rooms: {existing_setup.double_rooms}")
            print(f"  Total Capacity: {existing_setup.total_capacity}")
            return
        
        # Create vendor event accommodation setup
        total_capacity = event.single_rooms + (event.double_rooms * 2)
        
        vendor_setup = VendorEventAccommodation(
            tenant_id=event.tenant_id,
            vendor_accommodation_id=event.vendor_accommodation_id,
            event_id=event.id,
            event_name=event.title,
            single_rooms=event.single_rooms,
            double_rooms=event.double_rooms,
            total_capacity=total_capacity,
            current_occupants=0,
            is_active=True,
            created_by="fix_script"
        )
        
        db.add(vendor_setup)
        db.commit()
        db.refresh(vendor_setup)
        
        print(f"✅ Created vendor event accommodation setup:")
        print(f"  Setup ID: {vendor_setup.id}")
        print(f"  Event ID: {vendor_setup.event_id}")
        print(f"  Vendor ID: {vendor_setup.vendor_accommodation_id}")
        print(f"  Single Rooms: {vendor_setup.single_rooms}")
        print(f"  Double Rooms: {vendor_setup.double_rooms}")
        print(f"  Total Capacity: {vendor_setup.total_capacity}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_vendor_event_setup()