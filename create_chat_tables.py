#!/usr/bin/env python3
"""
Create chat tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_chat_tables():
    """Create chat tables"""
    
    tables_sql = [
        # Chat rooms table
        """
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id SERIAL PRIMARY KEY,
            chat_type VARCHAR(20) NOT NULL,
            name VARCHAR(255) NOT NULL,
            event_id INTEGER REFERENCES events(id),
            tenant_id VARCHAR(50) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """,
        
        # Chat messages table
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            chat_room_id INTEGER NOT NULL REFERENCES chat_rooms(id),
            sender_email VARCHAR(255) NOT NULL,
            sender_name VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            is_admin_message BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """,
        
        # Direct messages table
        """
        CREATE TABLE IF NOT EXISTS direct_messages (
            id SERIAL PRIMARY KEY,
            sender_email VARCHAR(255) NOT NULL,
            sender_name VARCHAR(255) NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            recipient_name VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            tenant_id VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_chat_rooms_tenant_id ON chat_rooms(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_rooms_event_id ON chat_rooms(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_room_id ON chat_messages(chat_room_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_direct_messages_recipient_email ON direct_messages(recipient_email)",
        "CREATE INDEX IF NOT EXISTS idx_direct_messages_sender_email ON direct_messages(sender_email)",
        "CREATE INDEX IF NOT EXISTS idx_direct_messages_tenant_id ON direct_messages(tenant_id)"
    ]
    
    try:
        with engine.connect() as conn:
            for i, sql in enumerate(tables_sql, 1):
                print(f"Creating table {i}/{len(tables_sql)}...")
                conn.execute(text(sql))
            
            for i, sql in enumerate(indexes_sql, 1):
                print(f"Creating index {i}/{len(indexes_sql)}...")
                conn.execute(text(sql))
            
            conn.commit()
            print("Chat tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_chat_tables()
    sys.exit(0 if success else 1)