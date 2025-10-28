#!/usr/bin/env python3
"""
Add is_read column to direct_messages table
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

from app.core.config import settings

def add_is_read_column():
    """Add is_read column to direct_messages table"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'direct_messages' 
                AND column_name = 'is_read';
            """))
            
            if result.fetchone():
                print("✅ is_read column already exists in direct_messages table")
                return True
            
            # Add the column
            print("Adding is_read column to direct_messages table...")
            conn.execute(text("""
                ALTER TABLE direct_messages 
                ADD COLUMN is_read BOOLEAN DEFAULT FALSE;
            """))
            conn.commit()
            print("✅ Added is_read column to direct_messages table")
            
            # Verify the column was added
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name = 'direct_messages' 
                AND column_name = 'is_read';
            """))
            
            column_info = result.fetchone()
            if column_info:
                print(f"✅ Verified: {column_info.column_name} ({column_info.data_type}) with default {column_info.column_default}")
            else:
                print("❌ Failed to verify column addition")
                return False
                
        return True
                
    except Exception as e:
        print(f"❌ Error adding is_read column: {e}")
        return False

if __name__ == "__main__":
    success = add_is_read_column()
    if success:
        print("🎉 Database update completed successfully!")
    else:
        print("💥 Database update failed!")
        sys.exit(1)