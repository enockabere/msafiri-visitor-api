#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def check_priority_enum():
    """Check if the priority enum exists and create it if needed"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if the enum type exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'notificationpriority'
                );
            """))
            
            exists = result.fetchone()[0]
            
            if not exists:
                print("Creating notificationpriority enum...")
                conn.execute(text("""
                    CREATE TYPE notificationpriority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
                """))
                conn.commit()
                print("Successfully created notificationpriority enum")
            else:
                print("notificationpriority enum already exists")
                
            # Show current values
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::notificationpriority)) as enum_value;
            """))
            
            print("Current notificationpriority enum values:")
            for row in result:
                print(f"  - {row.enum_value}")
                
    except Exception as e:
        print(f"Error with priority enum: {e}")

if __name__ == "__main__":
    check_priority_enum()