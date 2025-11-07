#!/usr/bin/env python3
"""
Manually upgrade user to super admin role
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal

def upgrade_user_to_super_admin():
    """Upgrade user to super admin role"""
    db: Session = SessionLocal()
    try:
        email = "msafiriapp@proton.me"
        
        # Check current user status
        result = db.execute(text("""
            SELECT id, email, role, status, is_active 
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
        
        # Update user to super admin
        if user.role != "super_admin":
            print(f"\nUpgrading user to super_admin...")
            
            db.execute(text("""
                UPDATE users 
                SET role = 'super_admin', 
                    status = 'active', 
                    is_active = true,
                    updated_at = NOW()
                WHERE email = :email
            """), {"email": email})
            
            db.commit()
            print("✅ User successfully upgraded to super_admin")
        else:
            print("\nUser is already a super_admin")
        
        # Also mark any pending admin invitations as accepted
        result = db.execute(text("""
            UPDATE admin_invitations 
            SET status = 'accepted', accepted_at = NOW()
            WHERE email = :email AND status = 'pending'
        """), {"email": email})
        
        if result.rowcount > 0:
            db.commit()
            print(f"✅ Marked {result.rowcount} admin invitation(s) as accepted")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    upgrade_user_to_super_admin()