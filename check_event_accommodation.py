#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db
from sqlalchemy import text

def check_event_accommodation():
    db = next(get_db())
    
    try:
        print("=== EVENT 68 DETAILS ===")
        event_query = text("""
            SELECT id, title, vendor_accommodation_id, tenant_id, status, start_date, end_date
            FROM events WHERE id = 68
        """)
        event = db.execute(event_query).fetchone()
        
        if event:
            print(f"Event ID: {event.id}")
            print(f"Title: {event.title}")
            print(f"Vendor Accommodation ID: {event.vendor_accommodation_id}")
            print(f"Tenant ID: {event.tenant_id}")
            print(f"Status: {event.status}")
            print(f"Start Date: {event.start_date}")
            print(f"End Date: {event.end_date}")
        else:
            print("Event 68 not found!")
            return
        
        print("\n=== VENDOR EVENT ACCOMMODATIONS FOR EVENT 68 ===")
        vea_query = text("""
            SELECT id, vendor_accommodation_id, event_id, event_name, 
                   single_rooms, double_rooms, total_capacity, current_occupants, is_active
            FROM vendor_event_accommodations 
            WHERE event_id = 68
        """)
        vea_results = db.execute(vea_query).fetchall()
        
        if vea_results:
            print(f"Found {len(vea_results)} vendor event accommodation setups:")
            for vea in vea_results:
                print(f"  Setup ID: {vea.id}")
                print(f"  Vendor Accommodation ID: {vea.vendor_accommodation_id}")
                print(f"  Event ID: {vea.event_id}")
                print(f"  Event Name: {vea.event_name}")
                print(f"  Single Rooms: {vea.single_rooms}")
                print(f"  Double Rooms: {vea.double_rooms}")
                print(f"  Total Capacity: {vea.total_capacity}")
                print(f"  Current Occupants: {vea.current_occupants}")
                print(f"  Is Active: {vea.is_active}")
                print("  ---")
        else:
            print("No vendor event accommodations found for event 68!")
            
        print("\n=== ALL VENDOR EVENT ACCOMMODATIONS ===")
        all_vea_query = text("""
            SELECT id, event_id, vendor_accommodation_id, event_name, single_rooms, double_rooms
            FROM vendor_event_accommodations 
            ORDER BY event_id
        """)
        all_vea = db.execute(all_vea_query).fetchall()
        
        print(f"Total vendor event accommodations in system: {len(all_vea)}")
        for vea in all_vea:
            print(f"  Setup ID: {vea.id}, Event: {vea.event_id}, Vendor: {vea.vendor_accommodation_id}, "
                  f"Event Name: {vea.event_name}, Single: {vea.single_rooms}, Double: {vea.double_rooms}")
            
        print("\n=== VENDOR ACCOMMODATIONS ===")
        va_query = text("""
            SELECT id, name, tenant_id, is_active
            FROM vendor_accommodations
            WHERE tenant_id = :tenant_id
        """)
        va_results = db.execute(va_query, {"tenant_id": event.tenant_id}).fetchall()
        
        print(f"Vendor accommodations for tenant {event.tenant_id}:")
        for va in va_results:
            print(f"  ID: {va.id}, Name: {va.name}, Active: {va.is_active}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_event_accommodation()