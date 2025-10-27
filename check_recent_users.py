#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.database import SessionLocal
from app import crud
from datetime import datetime, timedelta

def check_recent_users():
    """Check recently created users"""
    db = SessionLocal()
    
    try:
        # Get all users created in the last 24 hours
        from sqlalchemy import func
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        recent_users = db.query(crud.user.model).filter(
            crud.user.model.created_at >= yesterday
        ).order_by(crud.user.model.created_at.desc()).all()
        
        print(f"Found {len(recent_users)} users created in the last 24 hours:")
        print("="*80)
        
        for user in recent_users:
            print(f"Email: {user.email}")
            print(f"   ID: {user.id}")
            print(f"   Role: {user.role}")
            print(f"   Auth Provider: {user.auth_provider}")
            print(f"   Is Active: {user.is_active}")
            print(f"   Status: {user.status}")
            print(f"   Has Password: {user.hashed_password is not None}")
            print(f"   Created: {user.created_at}")
            print("-" * 50)
            
        # Also check admin invitations
        print("\nRecent Admin Invitations:")
        print("="*80)
        
        recent_invitations = db.query(crud.admin_invitation.model).filter(
            crud.admin_invitation.model.created_at >= yesterday
        ).order_by(crud.admin_invitation.model.created_at.desc()).all()
        
        for inv in recent_invitations:
            print(f"Email: {inv.email}")
            print(f"   Status: {inv.status}")
            print(f"   Invited By: {inv.invited_by}")
            print(f"   User Existed: {inv.user_existed}")
            print(f"   User ID: {inv.user_id}")
            print(f"   Created: {inv.created_at}")
            print(f"   Expires: {inv.expires_at}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_recent_users()