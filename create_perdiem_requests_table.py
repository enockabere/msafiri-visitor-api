#!/usr/bin/env python3
"""
Create perdiem requests table
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_perdiem_requests_table():
    """Create visitor-initiated perdiem requests table"""
    
    sql = """
    CREATE TABLE IF NOT EXISTS perdiem_requests (
        id SERIAL PRIMARY KEY,
        participant_id INTEGER NOT NULL REFERENCES event_participants(id),
        arrival_date DATE NOT NULL,
        departure_date DATE NOT NULL,
        calculated_days INTEGER NOT NULL,
        requested_days INTEGER NOT NULL,
        daily_rate DECIMAL(10,2) NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        justification TEXT,
        admin_notes TEXT,
        approved_by VARCHAR(255),
        payment_reference VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        UNIQUE(participant_id)
    )
    """
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_perdiem_requests_participant_id ON perdiem_requests(participant_id)",
        "CREATE INDEX IF NOT EXISTS idx_perdiem_requests_status ON perdiem_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_perdiem_requests_arrival_date ON perdiem_requests(arrival_date)"
    ]
    
    try:
        with engine.connect() as conn:
            print("Creating perdiem_requests table...")
            conn.execute(text(sql))
            
            for i, index_sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(index_sql))
            
            conn.commit()
            print("Perdiem requests table created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating table: {e}")
        return False

if __name__ == "__main__":
    success = create_perdiem_requests_table()
    sys.exit(0 if success else 1)