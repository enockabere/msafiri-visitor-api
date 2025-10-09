#!/usr/bin/env python3
"""
Direct SQL script to create participant_qr_codes table
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_qr_table():
    """Create the participant_qr_codes table directly"""
    engine = create_engine(settings.DATABASE_URL)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS participant_qr_codes (
        id SERIAL PRIMARY KEY,
        participant_id INTEGER NOT NULL UNIQUE,
        qr_token VARCHAR(255) NOT NULL UNIQUE,
        qr_data TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        FOREIGN KEY (participant_id) REFERENCES event_participants(id)
    );
    
    CREATE INDEX IF NOT EXISTS ix_participant_qr_codes_id ON participant_qr_codes(id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
            print("SUCCESS: participant_qr_codes table created successfully")
    except Exception as e:
        print(f"ERROR: Error creating table: {e}")

if __name__ == "__main__":
    create_qr_table()