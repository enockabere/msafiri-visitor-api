#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.tenant import Tenant

def check_tenants():
    try:
        db = SessionLocal()
        tenants = db.query(Tenant).all()
        
        print("=== TENANTS ===")
        for tenant in tenants:
            print(f"ID: {tenant.id}, Name: {tenant.name}, Slug: {tenant.slug}")
        
        if not tenants:
            print("No tenants found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    check_tenants()