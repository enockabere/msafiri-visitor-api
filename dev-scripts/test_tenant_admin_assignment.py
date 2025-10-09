#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.core.tenant_admin_assignment import assign_user_to_tenant_on_admin_change

def test_assignment():
    db: Session = SessionLocal()
    try:
        # Test with existing tenant and user
        tenant = db.query(Tenant).filter(Tenant.slug == "ko-oca").first()
        if not tenant:
            print("Tenant ko-oca not found")
            return
            
        print(f"Testing with tenant: {tenant.slug}")
        print(f"Current admin_email: {tenant.admin_email}")
        
        # Test the assignment function
        result = assign_user_to_tenant_on_admin_change(db, tenant)
        print(f"Assignment result: {result}")
        
        # Check user's tenant_id
        if tenant.admin_email:
            user = db.query(User).filter(User.email == tenant.admin_email).first()
            if user:
                print(f"User {user.email} tenant_id: {user.tenant_id}")
            else:
                print(f"User {tenant.admin_email} not found")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_assignment()