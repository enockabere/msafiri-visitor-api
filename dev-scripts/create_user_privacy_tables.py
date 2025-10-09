#!/usr/bin/env python3
"""
Create user privacy tables
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_user_privacy_tables():
    """Create user privacy and profile tables"""
    
    tables_sql = [
        # User profiles table
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
            profile_image_url VARCHAR(500),
            profile_image_filename VARCHAR(255),
            data_deleted BOOLEAN DEFAULT FALSE,
            data_deleted_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """,
        
        # Data deletion logs table
        """
        CREATE TABLE IF NOT EXISTS data_deletion_logs (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            user_id INTEGER NOT NULL,
            deletion_type VARCHAR(50) NOT NULL,
            tables_affected TEXT,
            deletion_summary TEXT,
            can_restore BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
        """
    ]
    
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_profiles_data_deleted ON user_profiles(data_deleted)",
        "CREATE INDEX IF NOT EXISTS idx_data_deletion_logs_user_email ON data_deletion_logs(user_email)",
        "CREATE INDEX IF NOT EXISTS idx_data_deletion_logs_user_id ON data_deletion_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_data_deletion_logs_deletion_type ON data_deletion_logs(deletion_type)"
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
            print("User privacy tables created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_user_privacy_tables()
    sys.exit(0 if success else 1)