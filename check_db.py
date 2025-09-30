#!/usr/bin/env python3
"""
Check what tables and columns exist in the database
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_database():
    """Check database structure"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if users table exists and its columns
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            if columns:
                print("Users table columns:")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]})")
            else:
                print("Users table does not exist")
                
            # Check all tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            tables = result.fetchall()
            print(f"\nAll tables: {[t[0] for t in tables]}")
            
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database()