#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.core.tenant_auto_assignment import auto_assign_tenant_admin

def test_auto_assignment():
    db: Session = SessionLocal()
    try:
        # Check current state
        print("=== BEFORE AUTO-ASSIGNMENT ===")
        users = db.query(User).filter(User.role.in_([UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN])).all()
        for user in users:
            print(f"User: {user.email}, Role: {user.role}, Tenant: {user.tenant_id}")
        
        tenants = db.query(Tenant).all()
        print("\n=== TENANTS ===")
        for tenant in tenants:
            print(f"Tenant: {tenant.slug}, Admin Email: {tenant.admin_email}")
        
        # Test auto-assignment for each admin user
        print("\n=== RUNNING AUTO-ASSIGNMENT ===")
        for user in users:
            result = auto_assign_tenant_admin(db, user)
            print(f"User {user.email}: {'ASSIGNED' if result else 'NO CHANGE'}")
        
        # Check final state
        print("\n=== AFTER AUTO-ASSIGNMENT ===")
        users = db.query(User).filter(User.role.in_([UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN])).all()
        for user in users:
            print(f"User: {user.email}, Role: {user.role}, Tenant: {user.tenant_id}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_auto_assignment()