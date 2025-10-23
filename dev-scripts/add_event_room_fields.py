#!/usr/bin/env python3
"""
Add expected_participants, single_rooms, and double_rooms columns to events table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def add_event_room_fields():
    """Add new room planning fields to events table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Add expected_participants column
            conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS expected_participants INTEGER;
            """))
            
            # Add single_rooms column
            conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS single_rooms INTEGER;
            """))
            
            # Add double_rooms column
            conn.execute(text("""
                ALTER TABLE events 
                ADD COLUMN IF NOT EXISTS double_rooms INTEGER;
            """))
            
            conn.commit()
            print("Successfully added room planning fields to events table")
            
        except Exception as e:
            print(f"Error adding room planning fields: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    add_event_room_fields()