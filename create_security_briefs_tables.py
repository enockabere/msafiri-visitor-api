#!/usr/bin/env python3
"""
Create security briefs tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_security_briefs_tables():
    """Create security briefs and acknowledgment tables"""
    
    tables_sql = [
        # Security briefs table
        """
        CREATE TABLE IF NOT EXISTS security_briefs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            brief_type VARCHAR(20) NOT NULL,
            content_type VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            event_id INTEGER REFERENCES events(id),
            is_active BOOLEAN DEFAULT TRUE,
            tenant_id VARCHAR(50) NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # User brief acknowledgments table
        """
        CREATE TABLE IF NOT EXISTS user_brief_acknowledgments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            brief_id INTEGER NOT NULL REFERENCES security_briefs(id),
            acknowledged_at VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(user_id, brief_id)
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_security_briefs_tenant_id ON security_briefs(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_security_briefs_brief_type ON security_briefs(brief_type)",
        "CREATE INDEX IF NOT EXISTS idx_security_briefs_event_id ON security_briefs(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_brief_acknowledgments_user_id ON user_brief_acknowledgments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_brief_acknowledgments_brief_id ON user_brief_acknowledgments(brief_id)"
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
            print("Security briefs tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_security_briefs_tables()
    sys.exit(0 if success else 1)