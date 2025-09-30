#!/usr/bin/env python3
"""
Create events table
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_events_table():
    """Create events table"""
    try:
        with engine.connect() as conn:
            # Create events table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    event_location VARCHAR(500) NOT NULL,
                    accommodation_details TEXT,
                    event_room_info TEXT,
                    food_info TEXT,
                    room_rate NUMERIC(10, 2),
                    other_facilities TEXT,
                    tenant_id VARCHAR NOT NULL REFERENCES tenants(slug),
                    created_by VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create index
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_events_tenant_id ON events(tenant_id)
            """))
            
            conn.commit()
            print("Events table created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating events table: {e}")
        return False

if __name__ == "__main__":
    success = create_events_table()
    sys.exit(0 if success else 1)