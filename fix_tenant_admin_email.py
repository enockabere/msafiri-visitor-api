#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.tenant import Tenant

def fix_tenant_admin_email():
    db: Session = SessionLocal()
    try:
        # Update ko-oca tenant admin_email to match the actual admin user
        tenant = db.query(Tenant).filter(Tenant.slug == "ko-oca").first()
        if tenant:
            print(f"Current admin_email: {tenant.admin_email}")
            tenant.admin_email = "maebaenock95@gmail.com"
            db.commit()
            print(f"Updated admin_email to: {tenant.admin_email}")
        else:
            print("ko-oca tenant not found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_tenant_admin_email()