#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_tables():
    """Check existing table structures"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if notifications table exists
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'notifications'
                ORDER BY ordinal_position;
            """))
            
            print("Notifications table columns:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
            
            # Check if events table exists
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'events'
                ORDER BY ordinal_position;
            """))
            
            print("\nEvents table columns:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_tables()