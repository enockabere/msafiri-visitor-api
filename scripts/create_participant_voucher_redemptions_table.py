#!/usr/bin/env python3
"""
Script to create participant_voucher_redemptions table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_table():
    """Create the participant_voucher_redemptions table"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to create the table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS participant_voucher_redemptions (
        id SERIAL PRIMARY KEY,
        allocation_id INTEGER NOT NULL REFERENCES event_allocations(id) ON DELETE CASCADE,
        participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_allocation 
        ON participant_voucher_redemptions(allocation_id);
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_participant 
        ON participant_voucher_redemptions(participant_id);
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_allocation_participant 
        ON participant_voucher_redemptions(allocation_id, participant_id);
    """
    
    try:
        with engine.connect() as connection:
            # Execute the SQL
            connection.execute(text(create_table_sql))
            connection.commit()
            print("Successfully created participant_voucher_redemptions table and indexes")
            
            # Verify table exists
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'participant_voucher_redemptions'
            """))
            
            if result.fetchone():
                print("Table verification successful")
                
                # Show table structure
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'participant_voucher_redemptions'
                    ORDER BY ordinal_position
                """))
                
                print("\nTable structure:")
                for row in result:
                    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                    default = f" DEFAULT {row[3]}" if row[3] else ""
                    print(f"  {row[0]}: {row[1]} {nullable}{default}")
                    
            else:
                print("Table verification failed")
                
    except Exception as e:
        print(f"Error creating table: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("Creating participant_voucher_redemptions table...")
    success = create_table()
    
    if success:
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed!")
        sys.exit(1)