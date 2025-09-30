#!/usr/bin/env python3
"""
Fix existing user data to have proper boolean values
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def fix_user_data():
    """Fix NULL boolean values in users table"""
    try:
        with engine.connect() as conn:
            # Update NULL auto_registered values to False
            result = conn.execute(text("""
                UPDATE users 
                SET auto_registered = FALSE 
                WHERE auto_registered IS NULL
            """))
            
            print(f"Updated {result.rowcount} users with NULL auto_registered")
            
            # Also fix any other NULL boolean fields
            conn.execute(text("""
                UPDATE users 
                SET is_active = TRUE 
                WHERE is_active IS NULL
            """))
            
            conn.commit()
            print("Fixed user data successfully!")
            return True
            
    except Exception as e:
        print(f"Error fixing user data: {e}")
        return False

if __name__ == "__main__":
    success = fix_user_data()
    sys.exit(0 if success else 1)