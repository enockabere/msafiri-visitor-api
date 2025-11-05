#!/usr/bin/env python3
"""
Simple fix for missing direct message notification
Direct SQL approach to avoid import issues
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

def fix_missing_notification():
    """Create missing notification using direct SQL"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost/msafiri_db')
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Find unread direct message from Leonard Kiprop
            result = conn.execute(text("""
                SELECT id, message, created_at 
                FROM direct_messages 
                WHERE sender_email = 'leonard.kiprop@oca.msf.org' 
                AND recipient_email = 'kenya-visitor@oca.msf.org' 
                AND is_read = false 
                ORDER BY created_at DESC 
                LIMIT 1
            """))
            
            message_row = result.fetchone()
            if not message_row:
                print("No unread message from Leonard Kiprop found")
                return
                
            print(f"Found message: {message_row[1][:50]}...")
            
            # Get recipient user ID
            user_result = conn.execute(text("""
                SELECT id, tenant_id 
                FROM users 
                WHERE email = 'kenya-visitor@oca.msf.org'
            """))
            
            user_row = user_result.fetchone()
            if not user_row:
                print("Recipient user not found")
                return
                
            user_id = user_row[0]
            tenant_id = user_row[1] or 'msf-global'
            
            # Check if notification already exists
            check_result = conn.execute(text("""
                SELECT id 
                FROM notifications 
                WHERE user_id = :user_id 
                AND title LIKE '%Leonard Kiprop%' 
                AND is_read = false
            """), {"user_id": user_id})
            
            if check_result.fetchone():
                print("Notification already exists")
                return
                
            # Create the notification
            message_text = message_row[1]
            truncated_message = message_text[:100] + ("..." if len(message_text) > 100 else "")
            
            conn.execute(text("""
                INSERT INTO notifications (
                    user_id, tenant_id, title, message, notification_type, 
                    priority, send_in_app, send_email, send_push, is_read, 
                    triggered_by, created_at, updated_at
                ) VALUES (
                    :user_id, :tenant_id, :title, :message, 'CHAT_MESSAGE', 
                    'MEDIUM', true, false, false, false, 
                    'leonard.kiprop@oca.msf.org', :created_at, :created_at
                )
            """), {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "title": "New direct message from Leonard Kiprop",
                "message": truncated_message,
                "created_at": message_row[2]
            })
            
            conn.commit()
            print("✅ Created notification successfully")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_missing_notification()