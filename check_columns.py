#!/usr/bin/env python3
"""Check if news_updates table has all required columns"""

from app.db.database import engine
from sqlalchemy import text

def check_columns():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'news_updates' 
            ORDER BY ordinal_position
        """))
        
        columns = [row[0] for row in result]
        required_columns = ['external_link', 'content_type', 'scheduled_publish_at', 'expires_at']
        
        print("Current news_updates columns:")
        for col in columns:
            print(f"  ✓ {col}")
        
        print("\nChecking required columns:")
        missing = []
        for req_col in required_columns:
            if req_col in columns:
                print(f"  ✓ {req_col}")
            else:
                print(f"  ✗ {req_col} - MISSING")
                missing.append(req_col)
        
        if missing:
            print(f"\n❌ Missing columns: {missing}")
            return False
        else:
            print(f"\n✅ All required columns present!")
            return True

if __name__ == "__main__":
    check_columns()