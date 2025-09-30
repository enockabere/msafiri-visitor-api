#!/usr/bin/env python3
"""
Create super admin with minimal required fields only
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.core.security import get_password_hash

def create_simple_admin():
    """Create super admin using raw SQL"""
    email = "superadmin@gmail.com"
    password = "SuperAdmin2025!"
    full_name = "Super Administrator"
    
    try:
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Use raw SQL to insert user
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO users (
                    email, hashed_password, full_name, role, status, 
                    is_active, auth_provider, auto_registered, created_at
                ) VALUES (
                    :email, :hashed_password, :full_name, :role, :status,
                    :is_active, :auth_provider, :auto_registered, NOW()
                ) RETURNING id, email, full_name, role
            """), {
                'email': email,
                'hashed_password': hashed_password,
                'full_name': full_name,
                'role': 'SUPER_ADMIN',
                'status': 'ACTIVE',
                'is_active': True,
                'auth_provider': 'LOCAL',
                'auto_registered': False
            })
            
            user = result.fetchone()
            conn.commit()
            
            print("Super admin created successfully!")
            print(f"ID: {user[0]}")
            print(f"Email: {user[1]}")
            print(f"Name: {user[2]}")
            print(f"Role: {user[3]}")
            print(f"Password: {password}")
            
            return True
            
    except Exception as e:
        print(f"Error creating admin: {e}")
        return False

if __name__ == "__main__":
    success = create_simple_admin()
    sys.exit(0 if success else 1)