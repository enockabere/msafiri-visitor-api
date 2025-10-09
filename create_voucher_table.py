#!/usr/bin/env python3
"""
Direct SQL script to create participant_voucher_redemptions table
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_voucher_table():
    """Create the participant_voucher_redemptions table directly"""
    engine = create_engine(settings.DATABASE_URL)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS participant_voucher_redemptions (
        id SERIAL PRIMARY KEY,
        allocation_id INTEGER NOT NULL,
        participant_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        redeemed_at TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (allocation_id) REFERENCES event_allocations(id),
        FOREIGN KEY (participant_id) REFERENCES event_participants(id)
    );
    
    CREATE INDEX IF NOT EXISTS ix_participant_voucher_redemptions_id ON participant_voucher_redemptions(id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
            print("SUCCESS: participant_voucher_redemptions table created successfully")
    except Exception as e:
        print(f"ERROR: Error creating table: {e}")

if __name__ == "__main__":
    create_voucher_table()