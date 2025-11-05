#!/usr/bin/env python3
"""
Fix missing direct message notification
Creates notification for Leonard Kiprop's direct message
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.chat import DirectMessage
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationPriority
from sqlalchemy import and_, desc

def fix_missing_notification():
    """Create missing notification for Leonard Kiprop's direct message"""
    
    db = next(get_db())
    
    try:
        # Find the unread direct message from Leonard Kiprop
        leonard_message = db.query(DirectMessage).filter(
            and_(
                DirectMessage.sender_email == "leonard.kiprop@oca.msf.org",
                DirectMessage.recipient_email == "kenya-visitor@oca.msf.org",
                DirectMessage.is_read == False
            )
        ).order_by(desc(DirectMessage.created_at)).first()
        
        if not leonard_message:
            print("No unread message from Leonard Kiprop found")
            return
            
        print(f"Found unread message: {leonard_message.message[:50]}...")
        
        # Get recipient user
        recipient = db.query(User).filter(
            User.email == "kenya-visitor@oca.msf.org"
        ).first()
        
        if not recipient:
            print("Recipient user not found")
            return
            
        # Check if notification already exists
        existing_notification = db.query(Notification).filter(
            and_(
                Notification.user_id == recipient.id,
                Notification.title.like("%Leonard Kiprop%"),
                Notification.is_read == False
            )
        ).first()
        
        if existing_notification:
            print("Notification already exists")
            return
            
        # Create the missing notification
        notification = Notification(
            user_id=recipient.id,
            tenant_id=recipient.tenant_id or "msf-global",
            title="New direct message from Leonard Kiprop",
            message=leonard_message.message[:100] + ("..." if len(leonard_message.message) > 100 else ""),
            notification_type=NotificationType.CHAT_MESSAGE,
            priority=NotificationPriority.MEDIUM,
            send_in_app=True,
            send_email=False,
            send_push=False,
            is_read=False,
            triggered_by="leonard.kiprop@oca.msf.org",
            created_at=leonard_message.created_at
        )
        
        db.add(notification)
        db.commit()
        
        print(f"✅ Created notification: {notification.title}")
        print(f"   Message: {notification.message}")
        print(f"   Created at: {notification.created_at}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_missing_notification()