# File: scripts/update_existing_users.py
"""
Script to update existing users after SSO migration
Run this AFTER applying the database migration
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User, AuthProvider, UserStatus, UserRole
from sqlalchemy import text

def update_existing_users():
    """Update existing users with new SSO fields"""
    db = SessionLocal()
    
    try:
        print("Updating existing users for SSO support...")
        
        # 1. Set auth_provider for existing users
        print("Setting auth_provider for existing users...")
        
        # Users with passwords are local auth
        result = db.execute(
            text("UPDATE users SET auth_provider = 'local' WHERE hashed_password IS NOT NULL")
        )
        print(f"Updated {result.rowcount} users to local auth")
        
        # Users without passwords (if any) are marked as local but inactive
        result = db.execute(
            text("UPDATE users SET auth_provider = 'local', is_active = false WHERE hashed_password IS NULL")
        )
        print(f"Updated {result.rowcount} users without passwords")
        
        # 2. Set status for all existing users to active
        result = db.execute(
            text("UPDATE users SET status = 'active' WHERE is_active = true")
        )
        print(f"Set {result.rowcount} users to active status")
        
        result = db.execute(
            text("UPDATE users SET status = 'inactive' WHERE is_active = false")
        )
        print(f"Set {result.rowcount} users to inactive status")
        
        # 3. Set auto_registered to false for existing users (they were manually created)
        result = db.execute(
            text("UPDATE users SET auto_registered = false")
        )
        print(f"Marked {result.rowcount} existing users as manually created")
        
        # 4. Show summary of users by role
        print("\nUser summary after update:")
        roles_count = db.execute(
            text("SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY count DESC")
        ).fetchall()
        
        for role, count in roles_count:
            print(f"  {role}: {count} users")
        
        # 5. Show auth provider summary
        print("\nAuth provider summary:")
        auth_count = db.execute(
            text("SELECT auth_provider, COUNT(*) as count FROM users GROUP BY auth_provider")
        ).fetchall()
        
        for provider, count in auth_count:
            print(f"  {provider}: {count} users")
        
        db.commit()
        print("\n✅ Successfully updated existing users for SSO support!")
        
    except Exception as e:
        print(f"❌ Error updating users: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_existing_users()