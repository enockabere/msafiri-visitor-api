#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.user import User, UserRole
from sqlalchemy.orm import Session

def restore_user_role():
    db = SessionLocal()
    try:
        # Find the user
        user = db.query(User).filter(User.email == 'abereenock95@gmail.com').first()
        if user:
            print(f'User found: ID={user.id}, Email={user.email}, Role={user.role}, Tenant={user.tenant_id}')
            
            # Update user role back to SUPER_ADMIN
            user.role = UserRole.SUPER_ADMIN
            db.commit()
            print('User role updated to SUPER_ADMIN')
            
            # Verify the change
            db.refresh(user)
            print(f'Verified: Role is now {user.role}')
        else:
            print('User not found')
    except Exception as e:
        print(f'Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    restore_user_role()