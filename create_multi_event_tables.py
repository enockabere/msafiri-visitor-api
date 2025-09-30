#!/usr/bin/env python3
"""
Create multi-event and perdiem tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_multi_event_tables():
    """Create multi-event management tables"""
    
    # First update events table to add duration and perdiem fields
    update_events_sql = """
    ALTER TABLE events 
    ADD COLUMN IF NOT EXISTS duration_days INTEGER,
    ADD COLUMN IF NOT EXISTS perdiem_rate DECIMAL(10,2)
    """
    
    tables_sql = [
        # Participant perdiem table
        """
        CREATE TABLE IF NOT EXISTS participant_perdiem (
            id SERIAL PRIMARY KEY,
            participant_id INTEGER NOT NULL REFERENCES event_participants(id),
            event_id INTEGER NOT NULL REFERENCES events(id),
            daily_rate DECIMAL(10,2) NOT NULL,
            duration_days INTEGER NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            approved BOOLEAN DEFAULT FALSE,
            paid BOOLEAN DEFAULT FALSE,
            approved_by VARCHAR(255),
            payment_reference VARCHAR(255),
            notes VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(participant_id, event_id)
        )
        """,
        
        # Event conflict checks table
        """
        CREATE TABLE IF NOT EXISTS event_conflict_checks (
            id SERIAL PRIMARY KEY,
            participant_email VARCHAR(255) NOT NULL,
            event_id INTEGER NOT NULL REFERENCES events(id),
            conflicting_event_id INTEGER NOT NULL REFERENCES events(id),
            conflict_type VARCHAR(50) NOT NULL,
            resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_participant_perdiem_participant_id ON participant_perdiem(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_perdiem_event_id ON participant_perdiem(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_participant_perdiem_approved ON participant_perdiem(approved)",
        "CREATE INDEX IF NOT EXISTS idx_event_conflict_checks_participant_email ON event_conflict_checks(participant_email)",
        "CREATE INDEX IF NOT EXISTS idx_events_duration_days ON events(duration_days)",
        "CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date)",
        "CREATE INDEX IF NOT EXISTS idx_events_end_date ON events(end_date)"
    ]
    
    try:
        with engine.connect() as conn:
            # Update events table
            print("Updating events table...")
            conn.execute(text(update_events_sql))
            
            # Create new tables
            for i, sql in enumerate(tables_sql, 1):
                print(f"Creating table {i}/{len(tables_sql)}...")
                conn.execute(text(sql))
            
            # Create indexes
            for i, sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(sql))
            
            conn.commit()
            print("Multi-event tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_multi_event_tables()
    sys.exit(0 if success else 1)