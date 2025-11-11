#!/usr/bin/env python3
"""
Server script to create all missing voucher-related tables
Run this on the server where the database is hosted
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_tables():
    """Create all missing voucher-related tables"""
    
    print(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to create both tables
    create_tables_sql = """
    -- Create participant_voucher_redemptions table
    CREATE TABLE IF NOT EXISTS participant_voucher_redemptions (
        id SERIAL PRIMARY KEY,
        allocation_id INTEGER NOT NULL REFERENCES event_allocations(id) ON DELETE CASCADE,
        participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        redeemed_at TIMESTAMP NOT NULL,
        redeemed_by VARCHAR(255),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create pending_voucher_redemptions table
    CREATE TABLE IF NOT EXISTS pending_voucher_redemptions (
        id SERIAL PRIMARY KEY,
        token VARCHAR(255) UNIQUE NOT NULL,
        allocation_id INTEGER NOT NULL REFERENCES event_allocations(id) ON DELETE CASCADE,
        participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL,
        notes TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        processed_at TIMESTAMP,
        processed_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for participant_voucher_redemptions
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_allocation 
        ON participant_voucher_redemptions(allocation_id);
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_participant 
        ON participant_voucher_redemptions(participant_id);
    CREATE INDEX IF NOT EXISTS idx_participant_voucher_redemptions_allocation_participant 
        ON participant_voucher_redemptions(allocation_id, participant_id);
    
    -- Create indexes for pending_voucher_redemptions
    CREATE INDEX IF NOT EXISTS idx_pending_voucher_redemptions_token 
        ON pending_voucher_redemptions(token);
    CREATE INDEX IF NOT EXISTS idx_pending_voucher_redemptions_allocation 
        ON pending_voucher_redemptions(allocation_id);
    CREATE INDEX IF NOT EXISTS idx_pending_voucher_redemptions_participant 
        ON pending_voucher_redemptions(participant_id);
    CREATE INDEX IF NOT EXISTS idx_pending_voucher_redemptions_status 
        ON pending_voucher_redemptions(status);
    """
    
    try:
        with engine.connect() as connection:
            # Execute the SQL
            connection.execute(text(create_tables_sql))
            connection.commit()
            print("✅ Successfully created all voucher tables and indexes")
            
            # Verify both tables exist
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('participant_voucher_redemptions', 'pending_voucher_redemptions')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"✅ Created tables: {', '.join(tables)}")
            
            if len(tables) == 2:
                print("✅ All tables verification successful")
            else:
                print("❌ Some tables missing")
                return False
                
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Creating all voucher-related tables...")
    success = create_tables()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("📱 Both allocations display and QR generation should now work properly.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)