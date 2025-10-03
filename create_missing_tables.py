#!/usr/bin/env python3
"""
Create only missing tables without dropping existing ones
This preserves your data
"""
from app.db.database import engine
from app.models.chat import ChatRoom, ChatMessage, DirectMessage
from app.models.admin_invitations import AdminInvitation
import sqlalchemy as sa

def create_missing_tables():
    """Create only the missing tables"""
    try:
        # Check what tables exist
        inspector = sa.inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"📋 Existing tables: {existing_tables}")
        
        # Create missing chat tables
        missing_tables = []
        
        if 'chat_rooms' not in existing_tables:
            ChatRoom.__table__.create(engine)
            missing_tables.append('chat_rooms')
            
        if 'chat_messages' not in existing_tables:
            ChatMessage.__table__.create(engine)
            missing_tables.append('chat_messages')
            
        if 'direct_messages' not in existing_tables:
            DirectMessage.__table__.create(engine)
            missing_tables.append('direct_messages')
            
        if 'admin_invitations' not in existing_tables:
            AdminInvitation.__table__.create(engine)
            missing_tables.append('admin_invitations')
        
        if missing_tables:
            print(f"✅ Created missing tables: {missing_tables}")
        else:
            print("✅ All tables already exist")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_missing_tables()