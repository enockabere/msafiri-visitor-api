#!/usr/bin/env python3
"""
Script to list all system users and their password status
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import SessionLocal

def list_users():
    """List all users and their password status"""
    
    try:
        db = SessionLocal()
        
        # Use raw SQL to avoid model relationship issues
        result = db.execute(text("""
            SELECT email, hashed_password, role, full_name 
            FROM users 
            ORDER BY email
        """))
        
        users = result.fetchall()
        
        print(f"\nTotal Users: {len(users)}")
        print("=" * 80)
        
        for user in users:
            has_password = "YES" if user.hashed_password else "NO"
            print(f"Email: {user.email:<40} | Password: {has_password} | Role: {user.role}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    list_users()