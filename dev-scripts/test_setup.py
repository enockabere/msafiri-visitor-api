#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def test_setup():
    """Test that all components are working"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Test that we can query the new tables
            result = connection.execute(text("SELECT COUNT(*) FROM event_participants"))
            participants_count = result.scalar()
            print(f"Event participants table: {participants_count} records")
            
            result = connection.execute(text("SELECT COUNT(*) FROM event_attachments"))
            attachments_count = result.scalar()
            print(f"Event attachments table: {attachments_count} records")
            
            result = connection.execute(text("SELECT COUNT(*) FROM events"))
            events_count = result.scalar()
            print(f"Events table: {events_count} records")
            
            print("All tables are accessible!")
            
            # Test notification service import
            try:
                from app.services.notification_service import send_event_notifications
                print("Notification service imported successfully!")
            except Exception as e:
                print(f"Notification service import failed: {e}")
            
            # Test models import
            try:
                from app.models.event_participant import EventParticipant
                from app.models.event_attachment import EventAttachment
                print("Models imported successfully!")
            except Exception as e:
                print(f"Models import failed: {e}")
                
            print("Setup verification completed!")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_setup()