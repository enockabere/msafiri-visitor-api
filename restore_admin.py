#!/usr/bin/env python3
"""
Script to restore user's SUPER_ADMIN role
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import SessionLocal

def restore_admin_role():
    """Restore user's SUPER_ADMIN role"""
    
    email = "maebaenock95@gmail.com"
    
    try:
        db = SessionLocal()
        
        # Check current role
        result = db.execute(text("""
            SELECT email, role, tenant_id, is_active 
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if not user:
            print(f"User {email} not found")
            return
        
        print(f"Current user status:")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Tenant: {user.tenant_id}")
        print(f"Active: {user.is_active}")
        
        # Restore SUPER_ADMIN role
        db.execute(text("""
            UPDATE users 
            SET role = 'SUPER_ADMIN' 
            WHERE email = :email
        """), {"email": email})
        
        db.commit()
        
        print(f"\nRestored {email} role to SUPER_ADMIN")
        
        # Verify the change
        result = db.execute(text("""
            SELECT role FROM users WHERE email = :email
        """), {"email": email})
        
        updated_user = result.fetchone()
        print(f"New role: {updated_user.role}")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    restore_admin_role()