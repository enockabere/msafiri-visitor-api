#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.user_roles import UserRole, RoleType
from app.core.config import settings

# Create database connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_user_roles(email: str):
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"👤 User: {user.email}")
        print(f"🔑 Single Role: {user.role} (value: {user.role.value if hasattr(user.role, 'value') else 'NO_VALUE'})")
        print(f"🏢 Tenant ID: {user.tenant_id}")
        print(f"✅ Is Active: {user.is_active}")
        
        # Check relationship roles
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.is_active == True
        ).all()
        
        print(f"🔗 Relationship Roles ({len(user_roles)}):")
        for role in user_roles:
            print(f"   - {role.role.value} (granted by: {role.granted_by}, active: {role.is_active})")
        
        # Check what roles are needed for events
        from app.models.user import UserRole as UserRoleEnum
        admin_roles_single = [UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN, UserRoleEnum.EVENT_ADMIN]
        admin_roles_relationship = [RoleType.MT_ADMIN, RoleType.HR_ADMIN, RoleType.EVENT_ADMIN]
        
        print(f"\n🎯 Event Creation Permission Check:")
        print(f"   Single role permission: {user.role in admin_roles_single}")
        print(f"   Relationship role permission: {any(role.role in admin_roles_relationship for role in user_roles)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_user_roles.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    check_user_roles(email)