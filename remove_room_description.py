#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.database import SessionLocal, engine
from sqlalchemy import text

def remove_room_description_column():
    """Remove description column from rooms table"""
    db = SessionLocal()
    
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'rooms' 
            AND column_name = 'description'
            AND table_schema = 'public'
        """)).fetchone()
        
        if result:
            print("✅ Description column exists in rooms table")
            
            # Remove the column
            db.execute(text("ALTER TABLE rooms DROP COLUMN IF EXISTS description"))
            db.commit()
            print("✅ Successfully removed description column from rooms table")
        else:
            print("✅ Description column does not exist in rooms table")
            
    except Exception as e:
        print(f"❌ Error removing description column: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    print("Removing description column from rooms table...")
    success = remove_room_description_column()
    
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")