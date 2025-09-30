#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant

def assign_tenant():
    db: Session = SessionLocal()
    try:
        # Find the user
        user = db.query(User).filter(User.email == "abereenock95@gmail.com").first()
        if not user:
            print("User not found")
            return
            
        # Find the tenant where this user is admin
        tenant = db.query(Tenant).filter(Tenant.admin_email == "abereenock95@gmail.com").first()
        if not tenant:
            print("No tenant found with this user as admin")
            return
            
        print(f"Assigning user {user.email} to tenant {tenant.slug}")
        user.tenant_id = tenant.slug
        db.commit()
        print(f"Successfully assigned tenant_id: {user.tenant_id}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    assign_tenant()