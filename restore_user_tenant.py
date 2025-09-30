#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.tenant import Tenant

def restore_and_check():
    db: Session = SessionLocal()
    try:
        # Restore user to ko-oca tenant
        user = db.query(User).filter(User.email == "maebaenock95@gmail.com").first()
        if user:
            user.tenant_id = "ko-oca"
            db.commit()
            print(f"Restored user {user.email} to tenant: {user.tenant_id}")
        
        # Check all tenant admin emails
        print("\n=== TENANT ADMIN EMAILS ===")
        tenants = db.query(Tenant).all()
        for tenant in tenants:
            print(f"Tenant: {tenant.slug}, Admin Email: {tenant.admin_email}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    restore_and_check()