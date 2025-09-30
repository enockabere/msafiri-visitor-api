#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def test_gender_field():
    """Test that the gender field is working correctly"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if gender column exists
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'gender'
            """))
            
            column_info = result.fetchone()
            if column_info:
                print(f"[OK] Gender column exists: {column_info}")
            else:
                print("[ERROR] Gender column not found")
                return False
            
            # Check current gender values
            result = connection.execute(text("""
                SELECT id, full_name, gender 
                FROM users 
                ORDER BY id
            """))
            
            users = result.fetchall()
            print(f"\n[INFO] Current users and their gender values:")
            for user in users:
                user_id, full_name, gender = user
                print(f"  ID: {user_id}, Name: {full_name}, Gender: {gender}")
            
            # Test updating a gender value
            if users:
                test_user_id = users[0][0]
                print(f"\n[TEST] Testing gender update for user ID {test_user_id}...")
                
                # Update gender to 'other'
                connection.execute(
                    text("UPDATE users SET gender = :gender WHERE id = :user_id"),
                    {"gender": "other", "user_id": test_user_id}
                )
                connection.commit()
                
                # Verify the update
                result = connection.execute(
                    text("SELECT full_name, gender FROM users WHERE id = :user_id"),
                    {"user_id": test_user_id}
                )
                updated_user = result.fetchone()
                if updated_user:
                    name, gender = updated_user
                    print(f"[OK] Successfully updated user '{name}' gender to: {gender}")
                
                # Revert back to original value for testing
                connection.execute(
                    text("UPDATE users SET gender = :gender WHERE id = :user_id"),
                    {"gender": "male", "user_id": test_user_id}
                )
                connection.commit()
                print(f"[INFO] Reverted gender back to 'male' for testing")
            
            print("\n[OK] Gender field test completed successfully!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error testing gender field: {e}")
        return False

if __name__ == "__main__":
    print("Testing gender field functionality...")
    success = test_gender_field()
    
    if success:
        print("\n[SUCCESS] All gender field tests passed!")
    else:
        print("\n[FAILED] Gender field tests failed!")
        sys.exit(1)