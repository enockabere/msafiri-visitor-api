#!/usr/bin/env python3
"""
Create item requests table
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_item_requests_table():
    """Create item requests table"""
    
    sql = """
    CREATE TABLE IF NOT EXISTS item_requests (
        id SERIAL PRIMARY KEY,
        participant_id INTEGER NOT NULL REFERENCES event_participants(id),
        allocation_id INTEGER NOT NULL REFERENCES participant_allocations(id),
        requested_quantity INTEGER NOT NULL DEFAULT 1,
        status VARCHAR(20) DEFAULT 'pending',
        notes VARCHAR(500),
        approved_by VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """
    
    index_sql = "CREATE INDEX IF NOT EXISTS idx_item_requests_status ON item_requests(status)"
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.execute(text(index_sql))
            conn.commit()
            print("Item requests table created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating table: {e}")
        return False

if __name__ == "__main__":
    success = create_item_requests_table()
    sys.exit(0 if success else 1)