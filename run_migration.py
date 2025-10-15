#!/usr/bin/env python3
"""
Script to run the room_type migration
"""
import os
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    """Run the room_type migration manually"""
    try:
        # Create database connection
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'accommodation_allocations' 
                AND column_name = 'room_type'
            """))
            
            if result.fetchone():
                print("[OK] room_type column already exists")
                return
            
            # Add the room_type column
            connection.execute(text("""
                ALTER TABLE accommodation_allocations 
                ADD COLUMN room_type VARCHAR(20)
            """))
            
            connection.commit()
            print("[OK] Successfully added room_type column to accommodation_allocations table")
            
    except Exception as e:
        print(f"[ERROR] Error running migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()