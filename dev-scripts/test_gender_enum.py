#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.user import Gender

def test_gender_enum():
    """Test that the Gender enum matches database values"""
    
    print("[INFO] Testing Gender enum values...")
    
    # Test enum values
    print(f"Gender.male.value = '{Gender.male.value}'")
    print(f"Gender.female.value = '{Gender.female.value}'")
    print(f"Gender.other.value = '{Gender.other.value}'")
    
    # Test creating enum from database values
    try:
        male_enum = Gender("male")
        female_enum = Gender("female")
        other_enum = Gender("other")
        print(f"[OK] Successfully created enums from database values")
        print(f"  male: {male_enum}")
        print(f"  female: {female_enum}")
        print(f"  other: {other_enum}")
    except ValueError as e:
        print(f"[ERROR] Failed to create enum from database value: {e}")
        return False
    
    # Test database compatibility
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Test that we can query users with gender values
            result = connection.execute(text("""
                SELECT id, full_name, gender 
                FROM users 
                WHERE gender IS NOT NULL
                LIMIT 3
            """))
            
            users = result.fetchall()
            print(f"\n[INFO] Sample users from database:")
            for user in users:
                user_id, full_name, gender = user
                try:
                    gender_enum = Gender(gender)
                    print(f"  ID: {user_id}, Name: {full_name}, Gender: {gender} -> Enum: {gender_enum}")
                except ValueError as e:
                    print(f"  ID: {user_id}, Name: {full_name}, Gender: {gender} -> [ERROR] {e}")
                    return False
            
            print(f"\n[SUCCESS] Gender enum is compatible with database values!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Gender enum compatibility...")
    success = test_gender_enum()
    
    if success:
        print("\n[SUCCESS] Gender enum test passed!")
    else:
        print("\n[FAILED] Gender enum test failed!")
        sys.exit(1)