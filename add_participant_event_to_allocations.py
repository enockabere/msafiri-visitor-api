#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_participant_event_columns():
    """Add participant_id and event_id columns to accommodation_allocations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    alter_table_sql = """
    -- Add participant_id column if it doesn't exist
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'accommodation_allocations' 
                      AND column_name = 'participant_id') THEN
            ALTER TABLE accommodation_allocations 
            ADD COLUMN participant_id INTEGER REFERENCES event_participants(id);
        END IF;
    END $$;
    
    -- Add event_id column if it doesn't exist
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'accommodation_allocations' 
                      AND column_name = 'event_id') THEN
            ALTER TABLE accommodation_allocations 
            ADD COLUMN event_id INTEGER REFERENCES events(id);
        END IF;
    END $$;
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_participant_id ON accommodation_allocations(participant_id);
    CREATE INDEX IF NOT EXISTS idx_accommodation_allocations_event_id ON accommodation_allocations(event_id);
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(alter_table_sql))
            connection.commit()
            print("Successfully added participant_id and event_id columns to accommodation_allocations table")
            
    except Exception as e:
        print(f"Error adding columns: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Adding participant_id and event_id columns to accommodation_allocations table...")
    success = add_participant_event_columns()
    
    if success:
        print("Column addition completed successfully!")
    else:
        print("Column addition failed!")
        sys.exit(1)