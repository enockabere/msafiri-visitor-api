#!/usr/bin/env python3
"""Create super admin user"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.user import User, UserRole, UserStatus, AuthProvider
from app.core.security import get_password_hash

def create_admin():
    """Create super admin user"""
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin exists
        existing_admin = db.query(User).filter(User.email == 'admin@msafiri.com').first()
        
        if not existing_admin:
            admin_user = User(
                email='admin@msafiri.com',
                hashed_password=get_password_hash('admin123'),
                full_name='Super Administrator',
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                auth_provider=AuthProvider.LOCAL,
                tenant_id='default'
            )
            
            db.add(admin_user)
            db.commit()
            print('✅ Super admin created: admin@msafiri.com / admin123')
        else:
            print('ℹ️  Super admin already exists')
            
    except Exception as e:
        print(f'❌ Error creating admin: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()