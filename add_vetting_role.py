#!/usr/bin/env python3
from sqlalchemy import text
from app.db.database import SessionLocal
from datetime import datetime

db = SessionLocal()
try:
    # Add VETTING_APPROVER role to user_roles table
    db.execute(text('''
        INSERT INTO user_roles (user_id, role, granted_by, is_active, granted_at, created_at, updated_at)
        SELECT 1, 'VETTING_APPROVER', 'system', true, :now, :now, :now
        WHERE NOT EXISTS (
            SELECT 1 FROM user_roles 
            WHERE user_id = 1 AND role = 'VETTING_APPROVER'
        )
    '''), {"now": datetime.now()})
    
    db.commit()
    print("Added VETTING_APPROVER role to user_roles table")
    
    # Verify the roles
    result = db.execute(text('''
        SELECT ur.role, ur.is_active, ur.granted_at
        FROM user_roles ur
        WHERE ur.user_id = 1
        ORDER BY ur.created_at DESC
    '''))
    
    roles = result.fetchall()
    print(f"User roles ({len(roles)} total):")
    for role in roles:
        status = "ACTIVE" if role.is_active else "INACTIVE"
        print(f"- {role.role} ({status}) - Added: {role.granted_at}")
    
finally:
    db.close()