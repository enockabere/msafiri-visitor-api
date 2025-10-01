#!/usr/bin/env python3
"""
Quick fix for notification priority enum issue
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.notification import NotificationPriority

def fix_notification_priorities():
    """Fix any existing notifications with incorrect priority values"""
    db = next(get_db())
    
    try:
        # Update any notifications with lowercase priority values
        db.execute("""
            UPDATE notifications 
            SET priority = UPPER(priority) 
            WHERE priority IN ('low', 'medium', 'high', 'urgent')
        """)
        db.commit()
        print("✅ Fixed existing notification priorities")
        
        # Show valid enum values
        print("\n📋 Valid NotificationPriority enum values:")
        for priority in NotificationPriority:
            print(f"  - {priority.value}")
            
    except Exception as e:
        print(f"❌ Error fixing priorities: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_notification_priorities()