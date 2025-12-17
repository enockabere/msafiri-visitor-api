#!/usr/bin/env python3
"""
Script to show all roles for a user
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import SessionLocal

def show_user_roles():
    """Show all roles for the user"""
    
    email = "maebaenock95@gmail.com"
    
    try:
        db = SessionLocal()
        
        # Get user's primary role
        result = db.execute(text("""
            SELECT id, email, role, tenant_id, is_active 
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if not user:
            print(f"User {email} not found")
            return
        
        print(f"User: {user.email}")
        print(f"Primary Role: {user.role}")
        print(f"Tenant: {user.tenant_id}")
        print(f"Active: {user.is_active}")
        print("=" * 50)
        
        # Get all roles from user_roles table
        result = db.execute(text("""
            SELECT ur.role, ur.is_active, ur.created_at
            FROM user_roles ur
            WHERE ur.user_id = :user_id
            ORDER BY ur.created_at DESC
        """), {"user_id": user.id})
        
        user_roles = result.fetchall()
        
        print(f"Additional Roles ({len(user_roles)} total):")
        if user_roles:
            for role in user_roles:
                status = "ACTIVE" if role.is_active else "INACTIVE"
                print(f"- {role.role} ({status}) - Added: {role.created_at}")
        else:
            print("- No additional roles found")
        
        print("=" * 50)
        
        # Check vetting committee roles
        result = db.execute(text("""
            SELECT vc.id, vc.event_id, vc.approver_email, vcm.email as member_email
            FROM vetting_committees vc
            LEFT JOIN vetting_committee_members vcm ON vc.id = vcm.committee_id
            WHERE vc.approver_email = :email OR vcm.email = :email
        """), {"email": email})
        
        vetting_roles = result.fetchall()
        
        print(f"Vetting Committee Roles ({len(vetting_roles)} total):")
        if vetting_roles:
            for role in vetting_roles:
                if role.approver_email == email:
                    print(f"- APPROVER for Committee {role.id} (Event {role.event_id})")
                if role.member_email == email:
                    print(f"- MEMBER of Committee {role.id} (Event {role.event_id})")
        else:
            print("- No vetting committee roles found")
        
        print("=" * 50)
        print("Summary of All Roles:")
        print(f"1. Primary Role: {user.role}")
        
        role_count = 2
        for role in user_roles:
            if role.is_active:
                print(f"{role_count}. Additional Role: {role.role}")
                role_count += 1
        
        if vetting_roles:
            for role in vetting_roles:
                if role.approver_email == email:
                    print(f"{role_count}. Vetting Role: APPROVER")
                    role_count += 1
                if role.member_email == email:
                    print(f"{role_count}. Vetting Role: COMMITTEE_MEMBER")
                    role_count += 1
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    show_user_roles()