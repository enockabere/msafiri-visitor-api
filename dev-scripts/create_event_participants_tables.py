#!/usr/bin/env python3
"""
Create event participants and checklist tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_event_participants_tables():
    """Create event participants and checklist tables"""
    try:
        with engine.connect() as conn:
            # Create event_participants table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS event_participants (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id),
                    email VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'invited',
                    invited_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create event_checklist_items table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS event_checklist_items (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id),
                    item_name VARCHAR(255) NOT NULL,
                    description VARCHAR(500),
                    is_required BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create participant_checklist_status table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS participant_checklist_status (
                    id SERIAL PRIMARY KEY,
                    participant_id INTEGER NOT NULL REFERENCES event_participants(id),
                    checklist_item_id INTEGER NOT NULL REFERENCES event_checklist_items(id),
                    is_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE,
                    UNIQUE(participant_id, checklist_item_id)
                )
            """))
            
            # Create indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_event_participants_event_id ON event_participants(event_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_event_checklist_items_event_id ON event_checklist_items(event_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_participant_checklist_status_participant_id ON participant_checklist_status(participant_id)
            """))
            
            conn.commit()
            print("Event participants and checklist tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_event_participants_tables()
    sys.exit(0 if success else 1)