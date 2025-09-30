#!/usr/bin/env python3

import os
import sys
from sqlalchemy.orm import Session

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal
from app.crud.notification import notification
from app.models.user import User

def test_notification_creation():
    """Test creating a CHAT_MESSAGE notification"""
    db = SessionLocal()
    
    try:
        # Get a test user
        user = db.query(User).filter(User.is_active == True).first()
        if not user:
            print("No active users found for testing")
            return
            
        print(f"Testing notification creation for user: {user.email}")
        print(f"User ID: {user.id}, Tenant: {user.tenant_id}")
        
        # Try to create a CHAT_MESSAGE notification
        created_notification = notification.create_user_notification(
            db=db,
            user_id=user.id,
            title="Test Chat Message",
            message="This is a test chat message notification",
            tenant_id=user.tenant_id or "system",
            notification_type="CHAT_MESSAGE",
            priority="LOW",
            send_email=False,
            send_push=False,
            action_url="/test/chat",
            triggered_by="test@example.com"
        )
        
        print(f"Successfully created notification ID: {created_notification.id}")
        print(f"Notification type: {created_notification.notification_type}")
        print(f"Priority: {created_notification.priority}")
        
    except Exception as e:
        print(f"Error creating notification: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_notification_creation()