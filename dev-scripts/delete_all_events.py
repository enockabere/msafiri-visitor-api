#!/usr/bin/env python3
"""
Delete all events for all tenants
WARNING: This will permanently delete all events and related data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal

def delete_all_events():
    """Delete all events and related data"""
    db: Session = SessionLocal()
    try:
        print("⚠️  WARNING: This will delete ALL events for ALL tenants!")
        print("This action cannot be undone.")
        
        # Get confirmation
        confirm = input("Type 'DELETE ALL EVENTS' to confirm: ")
        if confirm != "DELETE ALL EVENTS":
            print("❌ Operation cancelled")
            return
        
        # Get event count first
        result = db.execute(text("SELECT COUNT(*) FROM events"))
        event_count = result.scalar()
        
        if event_count == 0:
            print("ℹ️  No events found")
            return
        
        print(f"📊 Found {event_count} events to delete")
        
        # Delete related data first (to avoid foreign key constraints)
        print("🗑️  Deleting related data...")
        
        # Delete in order to respect foreign key constraints
        tables_to_clear = [
            "event_participants",
            "event_attachments", 
            "event_agenda",
            "event_food_menus",
            "event_feedback",
            "accommodation_bookings",
            "transport_requests",
            "chat_rooms",
            "notifications"
        ]
        
        for table in tables_to_clear:
            try:
                result = db.execute(text(f"DELETE FROM {table} WHERE event_id IN (SELECT id FROM events)"))
                if result.rowcount > 0:
                    print(f"   Deleted {result.rowcount} records from {table}")
            except Exception as e:
                print(f"   Warning: Could not clear {table}: {e}")
        
        # Delete events
        print("🗑️  Deleting events...")
        result = db.execute(text("DELETE FROM events"))
        deleted_count = result.rowcount
        
        # Commit all changes
        db.commit()
        
        print(f"✅ Successfully deleted {deleted_count} events and all related data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_events()