#!/usr/bin/env python3
"""
Create event allocations tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_event_allocations_tables():
    """Create event allocations tables"""
    try:
        with engine.connect() as conn:
            # Create event_items table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS event_items (
                    id SERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL REFERENCES events(id),
                    item_name VARCHAR(255) NOT NULL,
                    item_type VARCHAR(20) NOT NULL,
                    description VARCHAR(500),
                    total_quantity INTEGER NOT NULL DEFAULT 0,
                    allocated_quantity INTEGER NOT NULL DEFAULT 0,
                    created_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create participant_allocations table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS participant_allocations (
                    id SERIAL PRIMARY KEY,
                    participant_id INTEGER NOT NULL REFERENCES event_participants(id),
                    item_id INTEGER NOT NULL REFERENCES event_items(id),
                    allocated_quantity INTEGER NOT NULL DEFAULT 1,
                    redeemed_quantity INTEGER NOT NULL DEFAULT 0,
                    extra_requested INTEGER NOT NULL DEFAULT 0,
                    allocated_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create redemption_logs table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS redemption_logs (
                    id SERIAL PRIMARY KEY,
                    allocation_id INTEGER NOT NULL REFERENCES participant_allocations(id),
                    quantity_redeemed INTEGER NOT NULL,
                    redeemed_by VARCHAR(255) NOT NULL,
                    notes VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_event_items_event_id ON event_items(event_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_participant_allocations_participant_id ON participant_allocations(participant_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_participant_allocations_item_id ON participant_allocations(item_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_redemption_logs_allocation_id ON redemption_logs(allocation_id)
            """))
            
            conn.commit()
            print("Event allocations tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_event_allocations_tables()
    sys.exit(0 if success else 1)