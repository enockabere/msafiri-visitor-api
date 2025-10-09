#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def check_notification_enum():
    """Check the current notification enum values in the database"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if the enum type exists and what values it has
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::notificationtype)) as enum_value;
            """))
            
            print("Current notificationtype enum values:")
            for row in result:
                print(f"  - {row.enum_value}")
                
    except Exception as e:
        print(f"Error checking enum: {e}")
        # Try alternative query
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT enumlabel 
                    FROM pg_enum 
                    JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                    WHERE pg_type.typname = 'notificationtype';
                """))
                
                print("Current notificationtype enum values (alternative query):")
                for row in result:
                    print(f"  - {row.enumlabel}")
        except Exception as e2:
            print(f"Alternative query also failed: {e2}")

if __name__ == "__main__":
    check_notification_enum()