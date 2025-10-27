#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.admin_invitations import AdminInvitation
from app.models.user import User, UserRole
from datetime import datetime

def cleanup_admin_invitations():
    db: Session = SessionLocal()
    
    try:
        # Get all pending invitations
        pending_invitations = db.query(AdminInvitation).filter(
            AdminInvitation.status == "pending"
        ).all()
        
        print(f"Found {len(pending_invitations)} pending invitations")
        
        for invitation in pending_invitations:
            print(f"\n📧 Invitation: {invitation.email}")
            print(f"   Status: {invitation.status}")
            print(f"   Invited by: {invitation.invited_by}")
            print(f"   Created: {invitation.created_at}")
            
            # Check if user exists and has super admin role
            user = db.query(User).filter(User.email == invitation.email).first()
            
            if user:
                print(f"   User found - Role: {user.role}")
                
                if user.role == UserRole.SUPER_ADMIN:
                    # User is already super admin, mark invitation as accepted
                    print("   ✅ User is already super admin - marking invitation as accepted")
                    invitation.status = "accepted"
                    invitation.accepted_at = datetime.utcnow()
                    db.add(invitation)
                else:
                    print(f"   ⚠️  User exists but role is {user.role}, not SUPER_ADMIN")
                    action = input("   Mark invitation as accepted anyway? (y/n): ").strip().lower()
                    if action == 'y':
                        invitation.status = "accepted"
                        invitation.accepted_at = datetime.utcnow()
                        db.add(invitation)
                        print("   ✅ Invitation marked as accepted")
            else:
                print("   ❌ User not found")
                action = input("   Delete this invitation? (y/n): ").strip().lower()
                if action == 'y':
                    db.delete(invitation)
                    print("   🗑️  Invitation deleted")
        
        # Commit all changes
        db.commit()
        print("\n🎉 Cleanup completed!")
        
        # Show remaining pending invitations
        remaining = db.query(AdminInvitation).filter(
            AdminInvitation.status == "pending"
        ).count()
        print(f"📊 Remaining pending invitations: {remaining}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_admin_invitations()