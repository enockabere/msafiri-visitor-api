#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def remove_description_column():
    """Manually remove description column from guesthouses table"""
    try:
        # Create database connection
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'guesthouses' 
                AND column_name = 'description'
            """))
            
            if result.fetchone():
                # Column exists, drop it
                conn.execute(text("ALTER TABLE guesthouses DROP COLUMN description"))
                conn.commit()
                print("✅ Successfully removed description column from guesthouses table")
            else:
                print("ℹ️ Description column does not exist in guesthouses table")
                
    except Exception as e:
        print(f"❌ Error removing description column: {e}")

if __name__ == "__main__":
    remove_description_column()