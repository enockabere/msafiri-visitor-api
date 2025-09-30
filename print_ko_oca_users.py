#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User

def print_ko_oca_users():
    db: Session = SessionLocal()
    try:
        # Query users for ko-oca tenant
        users = db.query(User).filter(User.tenant_id == "ko-oca").all()
        
        print(f"\n=== KO-OCA TENANT USERS ({len(users)} total) ===")
        print("-" * 80)
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Full Name: {user.full_name}")
            print(f"Role: {user.role}")
            print(f"Tenant ID: {user.tenant_id}")
            print(f"Active: {user.is_active}")
            print(f"Created: {user.created_at}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print_ko_oca_users()