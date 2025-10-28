#!/usr/bin/env python3
"""Manually add missing columns to news_updates table"""

from app.db.database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            # Check existing columns
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'news_updates' 
                ORDER BY ordinal_position
            """))
            
            existing_columns = [row[0] for row in result]
            print("Existing columns:", existing_columns)
            
            # Add missing columns
            required_columns = {
                'external_link': 'VARCHAR(500)',
                'content_type': 'VARCHAR(20) DEFAULT \'text\'',
                'scheduled_publish_at': 'TIMESTAMP WITH TIME ZONE',
                'expires_at': 'TIMESTAMP WITH TIME ZONE'
            }
            
            for col_name, col_def in required_columns.items():
                if col_name not in existing_columns:
                    print(f"Adding column: {col_name}")
                    conn.execute(text(f'ALTER TABLE news_updates ADD COLUMN {col_name} {col_def}'))
                    conn.commit()
                else:
                    print(f"Column {col_name} already exists")
            
            print("✅ All columns added successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_columns()