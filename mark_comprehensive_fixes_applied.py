#!/usr/bin/env python3
"""
Mark comprehensive_fixes migration as applied without running it
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment variables")
    sys.exit(1)

print(f"Using database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")

def mark_migration_applied():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Insert the comprehensive_fixes revision into alembic_version table
        conn.execute(text("""
            INSERT INTO alembic_version (version_num) 
            VALUES ('comprehensive_fixes')
            ON CONFLICT (version_num) DO NOTHING
        """))
        conn.commit()
        print("✅ Marked comprehensive_fixes migration as applied")

if __name__ == "__main__":
    try:
        mark_migration_applied()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nAlternative: Run this SQL command directly in your database:")
        print("INSERT INTO alembic_version (version_num) VALUES ('comprehensive_fixes') ON CONFLICT (version_num) DO NOTHING;")
        sys.exit(1)