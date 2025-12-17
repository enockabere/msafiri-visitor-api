#!/usr/bin/env python3
"""
Script to check authentication token and user status
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import SessionLocal
from app.core.security import create_access_token, decode_token
from datetime import timedelta

def check_user_auth():
    """Check user authentication status and generate new token if needed"""
    
    email = "maebaenock95@gmail.com"
    
    try:
        db = SessionLocal()
        
        # Find user using raw SQL
        result = db.execute(text("""
            SELECT email, role, tenant_id, is_active 
            FROM users 
            WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if not user:
            print(f"User {email} not found")
            return
        
        print(f"User found: {user.email}")
        print(f"Role: {user.role}")
        print(f"Tenant: {user.tenant_id}")
        print(f"Active: {user.is_active}")
        
        # Generate new access token
        access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
        access_token = create_access_token(
            subject=user.email,
            tenant_id=user.tenant_id,
            expires_delta=access_token_expires
        )
        
        print(f"\nNew Access Token:")
        print(f"{access_token}")
        
        # Test token decoding
        payload = decode_token(access_token)
        if payload:
            print(f"\nToken validation successful")
            print(f"Token email: {payload.get('sub')}")
            print(f"Token tenant: {payload.get('tenant_id')}")
            print(f"Token expires: {payload.get('exp')}")
        else:
            print(f"\nToken validation failed")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    check_user_auth()