#!/usr/bin/env python3
"""
Find actual participants
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def find_participants():
    """Find actual participants"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check all participants
        result = conn.execute(text("SELECT id, event_id, full_name, status FROM event_participants ORDER BY id"))
        rows = result.fetchall()
        print(f"=== ALL PARTICIPANTS ===")
        print(f"Found {len(rows)} participants:")
        for row in rows:
            print(f"- ID: {row[0]}, Event: {row[1]}, Name: {row[2]}, Status: {row[3]}")
        
        # Check events
        result = conn.execute(text("SELECT id, title FROM events ORDER BY id"))
        rows = result.fetchall()
        print(f"\n=== ALL EVENTS ===")
        print(f"Found {len(rows)} events:")
        for row in rows:
            print(f"- ID: {row[0]}, Title: {row[1]}")

if __name__ == "__main__":
    find_participants()