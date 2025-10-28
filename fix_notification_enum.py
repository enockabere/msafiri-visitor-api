#!/usr/bin/env python3
"""
Fix notification enum to ensure APP_FEEDBACK value exists
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(__file__))

from app.core.config import settings

def fix_notification_enum():
    """Fix the notification enum to ensure APP_FEEDBACK exists"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # First, check current enum values
            print("Checking current enum values...")
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'notificationtype'
                ORDER BY enumlabel;
            """))
            
            current_values = [row.enumlabel for row in result]
            print(f"Current values: {current_values}")
            
            # Check if APP_FEEDBACK exists
            if 'APP_FEEDBACK' not in current_values:
                print("Adding APP_FEEDBACK to enum...")
                conn.execute(text("ALTER TYPE notificationtype ADD VALUE 'APP_FEEDBACK'"))
                conn.commit()
                print("✅ Added APP_FEEDBACK to enum")
            else:
                print("✅ APP_FEEDBACK already exists in enum")
                
            # Verify final state
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
                WHERE pg_type.typname = 'notificationtype'
                ORDER BY enumlabel;
            """))
            
            final_values = [row.enumlabel for row in result]
            print(f"Final values: {final_values}")
                
    except Exception as e:
        print(f"❌ Error fixing enum: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_notification_enum()
    if success:
        print("🎉 Notification enum fix completed successfully!")
    else:
        print("💥 Notification enum fix failed!")
        sys.exit(1)