#!/usr/bin/env python3
"""
Check database tables and structure
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def check_tables():
    """Check what tables exist in the database"""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    print("=== DATABASE TABLES ===")
    tables = inspector.get_table_names()
    for table in sorted(tables):
        print(f"- {table}")
    
    print("\n=== EVENT_ALLOCATIONS TABLE ===")
    if 'event_allocations' in tables:
        columns = inspector.get_columns('event_allocations')
        for col in columns:
            print(f"- {col['name']}: {col['type']}")
        
        # Check data
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM event_allocations LIMIT 5"))
            rows = result.fetchall()
            print(f"\nSample data ({len(rows)} rows):")
            for row in rows:
                print(f"- {row}")
    else:
        print("event_allocations table does not exist!")
    
    print("\n=== EVENT_PARTICIPANTS TABLE ===")
    if 'event_participants' in tables:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, event_id, full_name, status FROM event_participants WHERE id = 8"))
            rows = result.fetchall()
            print(f"Participant 8 data:")
            for row in rows:
                print(f"- {row}")

if __name__ == "__main__":
    check_tables()