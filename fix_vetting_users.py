#!/usr/bin/env python3
"""
Fix users with vetting_approver role
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_vetting_approver_users():
    """Fix users with vetting_approver role"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check current users with vetting_approver role
        result = conn.execute(text("SELECT id, email, role FROM users WHERE role = 'vetting_approver'"))
        users = result.fetchall()
        
        print(f"Found {len(users)} users with vetting_approver role:")
        for user in users:
            print(f"  - ID: {user[0]}, Email: {user[1]}, Role: {user[2]}")
        
        if users:
            # Temporarily change them to APPROVER role
            conn.execute(text("UPDATE users SET role = 'approver' WHERE role = 'vetting_approver'"))
            conn.commit()
            print(f"Updated {len(users)} users from vetting_approver to approver")
        else:
            print("No users found with vetting_approver role")

if __name__ == "__main__":
    fix_vetting_approver_users()