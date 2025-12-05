#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_description_column():
    """Check if description column exists in guesthouses table"""
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
            
            column = result.fetchone()
            if column:
                print("❌ Description column still exists in guesthouses table")
                return True
            else:
                print("✅ Description column does not exist in guesthouses table")
                return False
                
    except Exception as e:
        print(f"❌ Error checking description column: {e}")
        return None

if __name__ == "__main__":
    check_description_column()