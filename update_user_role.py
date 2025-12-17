#!/usr/bin/env python3
"""
Script to update user role to SUPER_ADMIN
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import SessionLocal

def update_user_role():
    """Update user role to SUPER_ADMIN"""
    
    email = "maebaenock95@gmail.com"
    
    try:
        db = SessionLocal()
        
        # Update user role to SUPER_ADMIN
        db.execute(text("""
            UPDATE users 
            SET role = 'SUPER_ADMIN' 
            WHERE email = :email
        """), {"email": email})
        
        db.commit()
        
        print(f"Updated {email} role to SUPER_ADMIN")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    update_user_role()