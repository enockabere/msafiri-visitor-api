#!/usr/bin/env python3
"""
Create visitor enhancement tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_visitor_enhancements_tables():
    """Create visitor enhancement tables"""
    
    tables_sql = [
        # Event contacts table
        """
        CREATE TABLE IF NOT EXISTS event_contacts (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            contact_type VARCHAR(20) NOT NULL,
            name VARCHAR(255) NOT NULL,
            title VARCHAR(255),
            phone VARCHAR(50) NOT NULL,
            email VARCHAR(255),
            department VARCHAR(255),
            availability VARCHAR(255),
            is_primary BOOLEAN DEFAULT FALSE,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Participant profiles table
        """
        CREATE TABLE IF NOT EXISTS participant_profiles (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id) UNIQUE,
            dietary_restrictions TEXT,
            food_allergies TEXT,
            medical_conditions TEXT,
            mobility_requirements TEXT,
            special_requests TEXT,
            emergency_contact_name VARCHAR(255),
            emergency_contact_phone VARCHAR(50),
            emergency_contact_relationship VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Chat message status table
        """
        CREATE TABLE IF NOT EXISTS chat_message_status (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES chat_messages(id),
            recipient_email VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'sent',
            status_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Notification queue table
        """
        CREATE TABLE IF NOT EXISTS notification_queue (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL,
            notification_type VARCHAR(30) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            sent BOOLEAN DEFAULT FALSE,
            sent_at TIMESTAMP WITH TIME ZONE,
            failed_attempts INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_event_contacts_event_id ON event_contacts(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_event_contacts_contact_type ON event_contacts(contact_type)",
        "CREATE INDEX IF NOT EXISTS idx_participant_profiles_participant_id ON participant_profiles(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_status_message_id ON chat_message_status(message_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_status_recipient ON chat_message_status(recipient_email)",
        "CREATE INDEX IF NOT EXISTS idx_notification_queue_recipient ON notification_queue(recipient_email)",
        "CREATE INDEX IF NOT EXISTS idx_notification_queue_sent ON notification_queue(sent)",
        "CREATE INDEX IF NOT EXISTS idx_notification_queue_type ON notification_queue(notification_type)"
    ]
    
    try:
        with engine.connect() as conn:
            for i, sql in enumerate(tables_sql, 1):
                print(f"Creating table {i}/{len(tables_sql)}...")
                conn.execute(text(sql))
            
            for i, sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(sql))
            
            conn.commit()
            print("Visitor enhancement tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_visitor_enhancements_tables()
    sys.exit(0 if success else 1)