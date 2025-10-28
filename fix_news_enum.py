#!/usr/bin/env python3
"""
Script to fix the news category enum by removing 'security' category
Run this on the server where the database is deployed
"""

import os
import psycopg2
from urllib.parse import urlparse

def fix_news_enum():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Parse the database URL
        parsed = urlparse(database_url)
        
        # Connect to database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password
        )
        
        cursor = conn.cursor()
        
        print("Connected to database successfully")
        
        # Check current enum values
        cursor.execute("SELECT unnest(enum_range(NULL::newscategory))")
        current_values = [row[0] for row in cursor.fetchall()]
        print(f"Current enum values: {current_values}")
        
        if 'security' not in current_values:
            print("✅ 'security' category already removed from enum")
            return True
        
        print("🔄 Updating enum to remove 'security' category...")
        
        # Create new enum type without 'security'
        cursor.execute("ALTER TYPE newscategory RENAME TO newscategory_old")
        cursor.execute("CREATE TYPE newscategory AS ENUM ('health_program', 'security_briefing', 'events', 'reports', 'general', 'announcement')")
        cursor.execute("ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::text::newscategory")
        cursor.execute("DROP TYPE newscategory_old")
        
        # Commit the changes
        conn.commit()
        
        print("✅ Successfully updated news category enum")
        
        # Verify the change
        cursor.execute("SELECT unnest(enum_range(NULL::newscategory))")
        new_values = [row[0] for row in cursor.fetchall()]
        print(f"New enum values: {new_values}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating enum: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🔧 Fixing news category enum...")
    success = fix_news_enum()
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("💥 Migration failed!")
        exit(1)