#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
try:
    # Update user's primary role back to SUPER_ADMIN
    db.execute(text('''
        UPDATE users 
        SET role = 'SUPER_ADMIN' 
        WHERE email = 'maebaenock95@gmail.com'
    '''))
    db.commit()
    print("Updated user role to SUPER_ADMIN")
    
    # Verify the change
    result = db.execute(text('''
        SELECT email, role, tenant_id 
        FROM users 
        WHERE email = 'maebaenock95@gmail.com'
    '''))
    user = result.fetchone()
    print(f"User: {user.email}, Role: {user.role}, Tenant: {user.tenant_id}")
    
finally:
    db.close()