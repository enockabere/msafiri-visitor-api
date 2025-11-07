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
        
        # Get event count first
        result = db.execute(text("SELECT COUNT(*) FROM events"))
        event_count = result.scalar()
        
        if event_count == 0:
            print("ℹ️  No events found")
            return
        
        print(f"📊 Found {event_count} events to delete")
        
        # Delete related data first (to avoid foreign key constraints)
        print("🗑️  Deleting related data...")
        
        # Delete in correct order to respect foreign key constraints
        deletion_queries = [
            "DELETE FROM participant_qr_codes WHERE participant_id IN (SELECT id FROM event_participants WHERE event_id IN (SELECT id FROM events))",
            "DELETE FROM accommodation_allocations WHERE participant_id IN (SELECT id FROM event_participants WHERE event_id IN (SELECT id FROM events))",
            "DELETE FROM agenda_feedback WHERE agenda_id IN (SELECT id FROM event_agenda WHERE event_id IN (SELECT id FROM events))",
            "DELETE FROM event_participants WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM event_attachments WHERE event_id IN (SELECT id FROM events)", 
            "DELETE FROM event_agenda WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM event_feedback WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM accommodation_bookings WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM transport_requests WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM chat_rooms WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM notifications WHERE event_id IN (SELECT id FROM events)",
            "DELETE FROM events"
        ]
        
        total_deleted = 0
        for query in deletion_queries:
            try:
                result = db.execute(text(query))
                if result.rowcount > 0:
                    table_name = query.split(" FROM ")[1].split(" ")[0]
                    print(f"   Deleted {result.rowcount} records from {table_name}")
                    if table_name == "events":
                        total_deleted = result.rowcount
            except Exception as e:
                table_name = query.split(" FROM ")[1].split(" ")[0]
                if "does not exist" in str(e):
                    print(f"   Skipped {table_name} (table does not exist)")
                else:
                    print(f"   Warning: Query failed for {table_name}: {e}")
                    db.rollback()
                    return
        
        # Commit all changes
        db.commit()
        
        print(f"✅ Successfully deleted {total_deleted} events and all related data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_events()