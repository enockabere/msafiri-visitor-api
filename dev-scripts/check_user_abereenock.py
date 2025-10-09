#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User

def check_user():
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "abereenock95@gmail.com").first()
        if user:
            print(f"User found:")
            print(f"  Email: {user.email}")
            print(f"  Full Name: {user.full_name}")
            print(f"  Role: {user.role}")
            print(f"  Tenant ID: {user.tenant_id}")
            print(f"  Active: {user.is_active}")
        else:
            print("User abereenock95@gmail.com not found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user()