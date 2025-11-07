#!/usr/bin/env python3
"""
Check user invitation status and fix role if needed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.user import UserRole

def check_user_status():
    """Check user status and invitation"""
    db: Session = SessionLocal()
    try:
        email = "msafiriapp@proton.me"
        
        # Check user details
        result = db.execute(text("""
            SELECT id, email, role, status, is_active, must_change_password 
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if user:
            print(f"User found:")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Role: {user.role}")
            print(f"  Status: {user.status}")
            print(f"  Active: {user.is_active}")
            print(f"  Must change password: {user.must_change_password}")
        else:
            print("User not found")
            return
        
        # Check invitation status
        result = db.execute(text("""
            SELECT id, email, status, invitation_token, user_existed, expires_at, created_at
            FROM admin_invitations 
            WHERE email = :email
            ORDER BY created_at DESC
            LIMIT 1
        """), {"email": email})
        
        invitation = result.fetchone()
        if invitation:
            print(f"\nInvitation found:")
            print(f"  ID: {invitation.id}")
            print(f"  Status: {invitation.status}")
            print(f"  User existed: {invitation.user_existed}")
            print(f"  Expires at: {invitation.expires_at}")
            print(f"  Created at: {invitation.created_at}")
            
            # If invitation is pending and user should be super admin, fix it
            if invitation.status == "pending" and user.role != "super_admin":
                print(f"\nFixing user role from {user.role} to super_admin...")
                
                # Update user role
                db.execute(text("""
                    UPDATE users 
                    SET role = 'super_admin', status = 'active', is_active = true
                    WHERE email = :email
                """), {"email": email})
                
                # Mark invitation as accepted
                db.execute(text("""
                    UPDATE admin_invitations 
                    SET status = 'accepted', accepted_at = NOW()
                    WHERE email = :email AND status = 'pending'
                """), {"email": email})
                
                db.commit()
                print("✅ User role updated to super_admin and invitation marked as accepted")
            else:
                print(f"\nNo action needed - Role: {user.role}, Invitation status: {invitation.status}")
        else:
            print("\nNo invitation found")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    check_user_status()