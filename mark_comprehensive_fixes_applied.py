#!/usr/bin/env python3
"""
Mark comprehensive_fixes migration as applied without running it
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/msafiri_db')

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
    mark_migration_applied()