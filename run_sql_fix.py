#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_registration_deadline():
    """Fix registration_deadline column to be datetime instead of date"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    sql_commands = [
        "ALTER TABLE events ADD COLUMN registration_deadline_temp TIMESTAMP;",
        "UPDATE events SET registration_deadline_temp = registration_deadline::timestamp;",
        "ALTER TABLE events DROP COLUMN registration_deadline;",
        "ALTER TABLE events RENAME COLUMN registration_deadline_temp TO registration_deadline;",
        "ALTER TABLE events ALTER COLUMN registration_deadline SET NOT NULL;"
    ]
    
    try:
        with engine.connect() as conn:
            for sql in sql_commands:
                print(f"Executing: {sql}")
                conn.execute(text(sql))
                conn.commit()
        
        print("Successfully changed registration_deadline to datetime!")
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_registration_deadline()