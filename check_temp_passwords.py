#!/usr/bin/env python3
"""
Script to check and set must_change_password flag for users with temporary passwords
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_and_fix_temp_passwords():
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check users who might have temporary passwords
        result = conn.execute(
            text("""
                SELECT id, email, role, must_change_password, auth_provider, created_at 
                FROM users 
                WHERE email = :email
            """),
            {"email": "kenya-visitor@oca.msf.org"}
        ).fetchone()
        
        if result:
            print(f"User found:")
            print(f"  ID: {result.id}")
            print(f"  Email: {result.email}")
            print(f"  Role: {result.role}")
            print(f"  Must change password: {result.must_change_password}")
            print(f"  Auth provider: {result.auth_provider}")
            print(f"  Created at: {result.created_at}")
            
            # If user doesn't have must_change_password set, set it
            if not result.must_change_password:
                print("Setting must_change_password = True")
                conn.execute(
                    text("UPDATE users SET must_change_password = true WHERE email = :email"),
                    {"email": "kenya-visitor@oca.msf.org"}
                )
                conn.commit()
                print("Updated successfully")
            else:
                print("User already has must_change_password = True")
        else:
            print("User not found")

if __name__ == "__main__":
    check_and_fix_temp_passwords()