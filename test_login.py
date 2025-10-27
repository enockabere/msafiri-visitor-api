#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.database import SessionLocal
from app import crud
from app.core.security import verify_password

def test_user_login(email: str, password: str):
    """Test if user can login with given credentials"""
    db = SessionLocal()
    
    try:
        # Get user by email
        user = crud.user.get_by_email(db, email=email)
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        print(f"✅ User found: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   Role: {user.role}")
        print(f"   Auth Provider: {user.auth_provider}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Status: {user.status}")
        print(f"   Has Password Hash: {user.hashed_password is not None}")
        
        if user.hashed_password:
            print(f"   Password Hash: {user.hashed_password[:50]}...")
            
            # Test password verification
            password_valid = verify_password(password, user.hashed_password)
            print(f"   Password Valid: {password_valid}")
            
            if password_valid:
                print(f"✅ Login would succeed for {email}")
                return True
            else:
                print(f"❌ Password verification failed for {email}")
                return False
        else:
            print(f"❌ No password hash found for {email}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing login: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_login.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    print(f"Testing login for: {email}")
    success = test_user_login(email, password)
    
    if success:
        print("🎉 Login test passed!")
    else:
        print("💥 Login test failed!")