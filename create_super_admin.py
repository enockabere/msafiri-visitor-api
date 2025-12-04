#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app import crud
from app.core.security import get_password_hash
from app.models.user import UserRole, AuthProvider, UserStatus
from app.schemas.user import UserCreate

def create_super_admin():
    """Create a super admin user"""
    db = SessionLocal()
    
    email = "maebaenock95@gmail.com"
    password = "Maeba1995"
    
    try:
        # Check if user already exists
        existing_user = crud.user.get_by_email(db, email=email)
        if existing_user:
            print(f"❌ User already exists: {email}")
            print(f"   Current role: {existing_user.role}")
            
            # Update to super admin if not already
            if existing_user.role != UserRole.SUPER_ADMIN:
                existing_user.role = UserRole.SUPER_ADMIN
                existing_user.hashed_password = get_password_hash(password)
                db.commit()
                print(f"✅ Updated existing user to SUPER_ADMIN")
            else:
                print(f"✅ User is already SUPER_ADMIN")
            return
        
        # Create new super admin user directly
        from app.models.user import User
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Super Admin",
            role=UserRole.SUPER_ADMIN,
            auth_provider=AuthProvider.LOCAL,
            status=UserStatus.ACTIVE,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Super admin created successfully!")
        print(f"   Email: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   Role: {user.role}")
        print(f"   Auth Provider: {user.auth_provider}")
        print(f"   Status: {user.status}")
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Creating super admin user...")
    create_super_admin()
    print("Done!")