#!/usr/bin/env python3
"""
Create event speakers and QR code tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_speakers_qr_tables():
    """Create speakers and QR code tables"""
    
    tables_sql = [
        # Event speakers table
        """
        CREATE TABLE IF NOT EXISTS event_speakers (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES events(id),
            name VARCHAR(255) NOT NULL,
            title VARCHAR(255),
            bio TEXT,
            email VARCHAR(255),
            phone VARCHAR(50),
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Participant QR codes table
        """
        CREATE TABLE IF NOT EXISTS participant_qr_codes (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id) UNIQUE,
            qr_token VARCHAR(255) NOT NULL UNIQUE,
            qr_data TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_event_speakers_event_id ON event_speakers(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_qr_codes_participant_id ON participant_qr_codes(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_qr_codes_qr_token ON participant_qr_codes(qr_token)"
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
            print("Speakers and QR tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_speakers_qr_tables()
    sys.exit(0 if success else 1)