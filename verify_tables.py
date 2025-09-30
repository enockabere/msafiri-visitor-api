#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def verify_tables():
    """Verify the new tables were created"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check event_participants table
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'event_participants'
                ORDER BY ordinal_position;
            """))
            
            print("Event participants table columns:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
            
            # Check event_attachments table
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'event_attachments'
                ORDER BY ordinal_position;
            """))
            
            print("\nEvent attachments table columns:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
                
            print("\nTables created successfully!")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    verify_tables()