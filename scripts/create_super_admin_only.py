# File: scripts/create_super_admin_only.py
"""
Create just the super admin user (after database reset)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, UserRole, AuthProvider, UserStatus
from app.core.security import get_password_hash

def create_super_admin():
    """Create the single super admin user"""
    print("👤 Creating super admin user...")
    
    # User credentials
    email = "abereenock95@gmail.com"
    password = "SuperAdmin2025!"
    full_name = "Super Administrator"
    
    try:
        db = SessionLocal()
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"⚠️  User {email} already exists!")
            print(f"   🆔 ID: {existing_user.id}")
            print(f"   👤 Name: {existing_user.full_name}")
            print(f"   🛡️  Role: {existing_user.role.value}")
            print(f"   ✅ Active: {existing_user.is_active}")
            return True
        
        # Create the user
        hashed_password = get_password_hash(password)
        
        super_admin = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            tenant_id=None,  # Super admin doesn't belong to any tenant
            auth_provider=AuthProvider.LOCAL
        )
        
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        
        print(f"✅ Super admin created successfully!")
        print()
        print(f"📋 LOGIN CREDENTIALS:")
        print(f"   📧 Email: {email}")
        print(f"   🔒 Password: {password}")
        print(f"   👤 Name: {full_name}")
        print(f"   🛡️  Role: Super Administrator")
        print(f"   🆔 Database ID: {super_admin.id}")
        print()
        print("🧪 TEST THESE FEATURES:")
        print("   1. Login at /docs or your frontend")
        print("   2. Test password reset with this email")
        print("   3. Change password after first login")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create super admin: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

def main():
    print("🔧 CREATING SUPER ADMIN USER")
    print("=" * 40)
    
    if create_super_admin():
        print("\n✅ SUPER ADMIN CREATED SUCCESSFULLY!")
        print("You can now test login and password reset.")
        return True
    else:
        print("\n❌ FAILED TO CREATE SUPER ADMIN!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)