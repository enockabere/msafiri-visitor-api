#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
try:
    result = db.execute(text('''
        SELECT id, email, role, tenant_id, is_active 
        FROM users 
        ORDER BY email
    '''))
    
    users = result.fetchall()
    print(f"Total users: {len(users)}")
    print("=" * 80)
    
    for user in users:
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Tenant: {user.tenant_id}")
        print(f"Active: {user.is_active}")
        print("-" * 40)
        
finally:
    db.close()