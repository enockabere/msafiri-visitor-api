#!/usr/bin/env python3
"""
Script to add test participants to an existing event
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def add_test_participants():
    """Add test participants to the first event found"""
    
    try:
        db = SessionLocal()
        
        # Get the first event using raw SQL
        result = db.execute(text("SELECT id, title FROM events LIMIT 1")).fetchone()
        if not result:
            print("No events found in database")
            return
        
        event_id, event_title = result
        print(f"Adding participants to event: {event_title}")
        
        # Test participants data
        test_participants = [
            {
                "email": "john.doe@msf.org",
                "full_name": "John Doe",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "registered",
                "country": "Kenya",
                "travelling_from_country": "Kenya",
                "position": "Project Coordinator",
                "project": "Nairobi Operations",
                "gender": "Male",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "jane.smith@msf.org",
                "full_name": "Jane Smith",
                "role": "speaker",
                "participant_role": "facilitator",
                "status": "selected",
                "country": "Uganda",
                "travelling_from_country": "Uganda",
                "position": "Medical Coordinator",
                "project": "Kampala Health Center",
                "gender": "Female",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "mike.johnson@msf.org",
                "full_name": "Mike Johnson",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "waiting",
                "country": "Tanzania",
                "travelling_from_country": "Tanzania",
                "position": "Logistics Officer",
                "project": "Dar es Salaam Supply Chain",
                "gender": "Male",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "sarah.wilson@msf.org",
                "full_name": "Sarah Wilson",
                "role": "organizer",
                "participant_role": "organizer",
                "status": "selected",
                "country": "Rwanda",
                "travelling_from_country": "Rwanda",
                "position": "Program Manager",
                "project": "Kigali Regional Office",
                "gender": "Female",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "david.brown@msf.org",
                "full_name": "David Brown",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "registered",
                "country": "Ethiopia",
                "travelling_from_country": "Ethiopia",
                "position": "Field Coordinator",
                "project": "Addis Ababa Emergency Response",
                "gender": "Male",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "lisa.garcia@msf.org",
                "full_name": "Lisa Garcia",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "declined",
                "country": "South Africa",
                "travelling_from_country": "South Africa",
                "position": "HR Specialist",
                "project": "Cape Town Regional HR",
                "gender": "Female",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "robert.taylor@msf.org",
                "full_name": "Robert Taylor",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "selected",
                "country": "Nigeria",
                "travelling_from_country": "Nigeria",
                "position": "Finance Manager",
                "project": "Lagos Financial Operations",
                "gender": "Male",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "maria.rodriguez@msf.org",
                "full_name": "Maria Rodriguez",
                "role": "speaker",
                "participant_role": "facilitator",
                "status": "selected",
                "country": "Ghana",
                "travelling_from_country": "Ghana",
                "position": "Training Coordinator",
                "project": "Accra Training Center",
                "gender": "Female",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "ahmed.hassan@msf.org",
                "full_name": "Ahmed Hassan",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "waiting",
                "country": "Egypt",
                "travelling_from_country": "Egypt",
                "position": "IT Specialist",
                "project": "Cairo IT Support",
                "gender": "Male",
                "invited_by": "admin@msf.org"
            },
            {
                "email": "fatima.ali@msf.org",
                "full_name": "Fatima Ali",
                "role": "attendee",
                "participant_role": "visitor",
                "status": "registered",
                "country": "Morocco",
                "travelling_from_country": "Morocco",
                "position": "Communications Officer",
                "project": "Rabat Communications Hub",
                "gender": "Female",
                "invited_by": "admin@msf.org"
            }
        ]
        
        # Check if participants already exist
        existing_count = db.execute(text("SELECT COUNT(*) FROM event_participants WHERE event_id = :event_id"), {"event_id": event_id}).scalar()
        if existing_count > 0:
            print(f"Event already has {existing_count} participants. Adding more...")
        
        # Add participants
        added_count = 0
        for participant_data in test_participants:
            # Check if participant already exists
            existing = db.execute(text(
                "SELECT id FROM event_participants WHERE event_id = :event_id AND email = :email"
            ), {"event_id": event_id, "email": participant_data["email"]}).fetchone()
            
            if existing:
                print(f"Skipping {participant_data['full_name']} - already exists")
                continue
            
            # Insert participant using raw SQL
            db.execute(text("""
                INSERT INTO event_participants (
                    event_id, email, full_name, role, participant_role, status,
                    country, travelling_from_country, position, project, gender, invited_by,
                    created_at, updated_at
                ) VALUES (
                    :event_id, :email, :full_name, :role, :participant_role, :status,
                    :country, :travelling_from_country, :position, :project, :gender, :invited_by,
                    :created_at, :updated_at
                )
            """), {
                "event_id": event_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                **participant_data
            })
            
            added_count += 1
            print(f"Added {participant_data['full_name']} ({participant_data['status']})")
        
        db.commit()
        
        total_count = db.execute(text("SELECT COUNT(*) FROM event_participants WHERE event_id = :event_id"), {"event_id": event_id}).scalar()
        print(f"\nSuccessfully added {added_count} new participants!")
        print(f"Total participants in event: {total_count}")
        
        # Show status breakdown
        statuses = db.execute(text(
            "SELECT status, COUNT(*) FROM event_participants WHERE event_id = :event_id GROUP BY status"
        ), {"event_id": event_id}).fetchall()
        
        print("\nStatus breakdown:")
        for status, count in statuses:
            print(f"   {status}: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    add_test_participants()