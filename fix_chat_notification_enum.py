#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def fix_notification_enum():
    """Add CHAT_MESSAGE to the notification enum"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Add CHAT_MESSAGE to the enum
            print("Adding CHAT_MESSAGE to notificationtype enum...")
            conn.execute(text("ALTER TYPE notificationtype ADD VALUE 'CHAT_MESSAGE';"))
            conn.commit()
            print("Successfully added CHAT_MESSAGE to enum")
            
            # Verify the change
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::notificationtype)) as enum_value;
            """))
            
            print("\nUpdated notificationtype enum values:")
            for row in result:
                print(f"  - {row.enum_value}")
                
    except Exception as e:
        print(f"Error updating enum: {e}")
        if "already exists" in str(e):
            print("CHAT_MESSAGE already exists in enum")

if __name__ == "__main__":
    fix_notification_enum()