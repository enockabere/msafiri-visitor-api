#!/usr/bin/env python3
"""
Upgrade specific user to SUPER_ADMIN role
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal

def upgrade_user_to_super_admin():
    """Upgrade user to SUPER_ADMIN role"""
    db: Session = SessionLocal()
    try:
        email = "maebaenock95@gmail.com"
        
        # Check current user status
        result = db.execute(text("""
            SELECT id, email, role, status, is_active, tenant_id
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if not user:
            print(f"User {email} not found")
            return
        
        print(f"Current user status:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
        print(f"  Status: {user.status}")
        print(f"  Active: {user.is_active}")
        print(f"  Tenant: {user.tenant_id}")
        
        # Update user to SUPER_ADMIN
        if user.role != "SUPER_ADMIN":
            print(f"\nUpgrading user to SUPER_ADMIN...")
            
            db.execute(text("""
                UPDATE users 
                SET role = 'SUPER_ADMIN', 
                    updated_at = NOW()
                WHERE email = :email
            """), {"email": email})
            
            db.commit()
            print("User successfully upgraded to SUPER_ADMIN")
        else:
            print("\nUser is already a SUPER_ADMIN")
        
        # Verify the update
        result = db.execute(text("""
            SELECT id, email, role, status, is_active, tenant_id
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        updated_user = result.fetchone()
        print(f"\nUpdated user status:")
        print(f"  ID: {updated_user.id}")
        print(f"  Email: {updated_user.email}")
        print(f"  Role: {updated_user.role}")
        print(f"  Status: {updated_user.status}")
        print(f"  Active: {updated_user.is_active}")
        print(f"  Tenant: {updated_user.tenant_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    upgrade_user_to_super_admin()