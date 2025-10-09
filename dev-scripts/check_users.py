#!/usr/bin/env python3
"""
Check if users exist in the database
"""
import sys
import os
sys.path.append('.')

from app.db.database import SessionLocal
from app.models.user import User

def check_users():
    """List all users in the database"""
    try:
        db = SessionLocal()
        
        users = db.query(User).all()
        
        if not users:
            print("No users found in database")
            return
            
        print(f"Found {len(users)} user(s):")
        print("-" * 50)
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.full_name}")
            print(f"Role: {user.role.value}")
            print(f"Status: {user.status.value}")
            print(f"Active: {user.is_active}")
            print(f"Created: {user.created_at}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error checking users: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    check_users()