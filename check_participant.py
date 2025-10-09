#!/usr/bin/env python3
"""
Check participant 8 details
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def check_participant():
    """Check participant 8 and related data"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check participant 8
        result = conn.execute(text("SELECT * FROM event_participants WHERE id = 8"))
        rows = result.fetchall()
        print(f"=== PARTICIPANT 8 ===")
        if rows:
            for row in rows:
                print(f"- {row}")
        else:
            print("- Participant 8 not found!")
        
        # Check all participants for event 41
        result = conn.execute(text("SELECT id, event_id, full_name, status FROM event_participants WHERE event_id = 41"))
        rows = result.fetchall()
        print(f"\n=== PARTICIPANTS FOR EVENT 41 ===")
        print(f"Found {len(rows)} participants:")
        for row in rows:
            print(f"- {row}")
        
        # Check allocations for event 41
        result = conn.execute(text("SELECT * FROM event_allocations WHERE event_id = 41"))
        rows = result.fetchall()
        print(f"\n=== ALLOCATIONS FOR EVENT 41 ===")
        print(f"Found {len(rows)} allocations:")
        for row in rows:
            print(f"- {row}")

if __name__ == "__main__":
    check_participant()