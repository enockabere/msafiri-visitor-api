#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, UserRole, AuthProvider
from app.core.security import get_password_hash, verify_password

def fix_super_admin_user():
    db: Session = SessionLocal()
    
    try:
        # Email to check/fix
        email = input("Enter the super admin email: ").strip()
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User {email} not found")
            create = input("Create new super admin user? (y/n): ").strip().lower()
            if create == 'y':
                # Create new user
                hashed_password = get_password_hash("password@1234")
                user = User(
                    email=email,
                    hashed_password=hashed_password,
                    role=UserRole.SUPER_ADMIN,
                    auth_provider=AuthProvider.LOCAL,
                    is_active=True,
                    is_verified=True
                )
                db.add(user)
                db.commit()
                print(f"✅ Created super admin user: {email}")
                print(f"🔑 Password: password@1234")
            return
        
        print(f"✅ User found: {email}")
        print(f"   Role: {user.role}")
        print(f"   Auth Provider: {user.auth_provider}")
        print(f"   Active: {user.is_active}")
        # Check if user has email_verified_at field instead of is_verified
        if hasattr(user, 'email_verified_at'):
            print(f"   Email Verified: {user.email_verified_at is not None}")
        elif hasattr(user, 'is_verified'):
            print(f"   Verified: {user.is_verified}")
        
        # Test current password
        if user.hashed_password:
            password_works = verify_password("password@1234", user.hashed_password)
            print(f"   Password 'password@1234' works: {password_works}")
            
            if not password_works:
                fix = input("Fix password? (y/n): ").strip().lower()
                if fix == 'y':
                    user.hashed_password = get_password_hash("password@1234")
                    user.auth_provider = AuthProvider.LOCAL
                    db.commit()
                    print("✅ Password fixed")
        else:
            print("   No password set")
            fix = input("Set password? (y/n): ").strip().lower()
            if fix == 'y':
                user.hashed_password = get_password_hash("password@1234")
                user.auth_provider = AuthProvider.LOCAL
                db.commit()
                print("✅ Password set")
        
        # Fix other fields if needed
        if user.role != UserRole.SUPER_ADMIN:
            print(f"   Current role: {user.role}")
            upgrade = input(f"Upgrade role from {user.role} to SUPER_ADMIN? (y/n): ").strip().lower()
            if upgrade == 'y':
                user.role = UserRole.SUPER_ADMIN
                print("✅ Role updated to SUPER_ADMIN")
        
        if not user.is_active:
            user.is_active = True
            print("✅ User activated")
            
        # Handle verification field
        if hasattr(user, 'email_verified_at') and user.email_verified_at is None:
            from datetime import datetime
            user.email_verified_at = datetime.utcnow()
            print("✅ User email verified")
        elif hasattr(user, 'is_verified') and not user.is_verified:
            user.is_verified = True
            print("✅ User verified")
            
        db.commit()
        print(f"\n🎉 User {email} is ready to login with password: password@1234")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_super_admin_user()