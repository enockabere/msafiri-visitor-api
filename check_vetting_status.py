#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
try:
    # Check vetting status for the event
    result = db.execute(text('''
        SELECT id, event_id, status, submitted_at, submitted_by, approved_at, approved_by
        FROM vetting_committees 
        ORDER BY created_at DESC
        LIMIT 5
    '''))
    
    committees = result.fetchall()
    print(f"Vetting Committees ({len(committees)} total):")
    print("=" * 80)
    
    for committee in committees:
        print(f"ID: {committee.id}")
        print(f"Event ID: {committee.event_id}")
        print(f"Status: {committee.status}")
        print(f"Submitted At: {committee.submitted_at}")
        print(f"Submitted By: {committee.submitted_by}")
        print(f"Approved At: {committee.approved_at}")
        print(f"Approved By: {committee.approved_by}")
        print("-" * 40)
        
finally:
    db.close()