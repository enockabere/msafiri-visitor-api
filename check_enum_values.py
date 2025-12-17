#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
try:
    # Check what enum values exist in the database
    result = db.execute(text('''
        SELECT enumlabel 
        FROM pg_enum 
        WHERE enumtypid = (
            SELECT oid 
            FROM pg_type 
            WHERE typname = 'roletype'
        )
        ORDER BY enumlabel
    '''))
    
    enum_values = [row[0] for row in result.fetchall()]
    print("Current RoleType enum values in database:")
    for value in enum_values:
        print(f"- {value}")
    
finally:
    db.close()