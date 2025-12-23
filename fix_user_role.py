#!/usr/bin/env python3
"""
Quick script to fix the role of kenya-visitor@oca.msf.org
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_user_role():
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check current role
        result = conn.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": "kenya-visitor@oca.msf.org"}
        ).fetchone()
        
        if result:
            print(f"Current user: ID={result.id}, Email={result.email}, Role={result.role}")
            
            # Update role to VETTING_COMMITTEE
            conn.execute(
                text("UPDATE users SET role = 'VETTING_COMMITTEE' WHERE email = :email"),
                {"email": "kenya-visitor@oca.msf.org"}
            )
            conn.commit()
            
            print("Updated role to VETTING_COMMITTEE")
        else:
            print("User not found")

if __name__ == "__main__":
    fix_user_role()