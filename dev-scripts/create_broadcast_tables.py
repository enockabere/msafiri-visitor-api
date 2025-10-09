#!/usr/bin/env python3
"""
Create broadcast tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_broadcast_tables():
    """Create broadcast and read tracking tables"""
    
    tables_sql = [
        # Broadcasts table
        """
        CREATE TABLE IF NOT EXISTS broadcasts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            broadcast_type VARCHAR(20) NOT NULL,
            priority VARCHAR(10) DEFAULT 'normal',
            tenant_id VARCHAR(50) NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Broadcast reads table
        """
        CREATE TABLE IF NOT EXISTS broadcast_reads (
            id SERIAL PRIMARY KEY,
            broadcast_id INTEGER NOT NULL REFERENCES broadcasts(id),
            user_email VARCHAR(255) NOT NULL,
            read_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(broadcast_id, user_email)
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_tenant_id ON broadcasts(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_is_active ON broadcasts(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_expires_at ON broadcasts(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_broadcasts_priority ON broadcasts(priority)",
        "CREATE INDEX IF NOT EXISTS idx_broadcast_reads_broadcast_id ON broadcast_reads(broadcast_id)",
        "CREATE INDEX IF NOT EXISTS idx_broadcast_reads_user_email ON broadcast_reads(user_email)"
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
            print("Broadcast tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_broadcast_tables()
    sys.exit(0 if success else 1)