#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_direct_messages_table():
    """Create the missing direct_messages table"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # SQL to create direct_messages table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS direct_messages (
            id SERIAL PRIMARY KEY,
            sender_email VARCHAR(255) NOT NULL,
            sender_name VARCHAR(255),
            recipient_email VARCHAR(255) NOT NULL,
            recipient_name VARCHAR(255),
            message TEXT NOT NULL,
            tenant_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_direct_messages_sender ON direct_messages(sender_email);
        CREATE INDEX IF NOT EXISTS idx_direct_messages_recipient ON direct_messages(recipient_email);
        CREATE INDEX IF NOT EXISTS idx_direct_messages_tenant ON direct_messages(tenant_id);
        """
        
        # Execute the SQL
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        
        print("SUCCESS: direct_messages table created successfully")
        return True
        
    except Exception as e:
        print(f"ERROR: Error creating direct_messages table: {e}")
        return False

if __name__ == "__main__":
    success = create_direct_messages_table()
    sys.exit(0 if success else 1)