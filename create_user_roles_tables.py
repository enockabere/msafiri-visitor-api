#!/usr/bin/env python3
"""
Create user roles tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_user_roles_tables():
    """Create user roles and change log tables"""
    
    tables_sql = [
        # User roles table
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            role VARCHAR(20) NOT NULL,
            granted_by VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            granted_at TIMESTAMP WITH TIME ZONE NOT NULL,
            revoked_at TIMESTAMP WITH TIME ZONE,
            revoked_by VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(user_id, role, is_active) DEFERRABLE INITIALLY DEFERRED
        )
        """,
        
        # Role change logs table
        """
        CREATE TABLE IF NOT EXISTS role_change_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            user_email VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            action VARCHAR(20) NOT NULL,
            performed_by VARCHAR(255) NOT NULL,
            reason VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role)",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_is_active ON user_roles(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_role_change_logs_user_id ON role_change_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_role_change_logs_user_email ON role_change_logs(user_email)",
        "CREATE INDEX IF NOT EXISTS idx_role_change_logs_action ON role_change_logs(action)"
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
            print("User roles tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_user_roles_tables()
    sys.exit(0 if success else 1)