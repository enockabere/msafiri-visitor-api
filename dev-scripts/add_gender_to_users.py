#!/usr/bin/env python3

import os
import sys
import random
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_gender_column():
    """Add gender column to users table and populate with random values"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # First, add the gender column
    alter_table_sql = """
    -- Add gender column if it doesn't exist
    DO $$ 
    BEGIN 
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'users' 
                      AND column_name = 'gender') THEN
            -- Create the enum type first
            CREATE TYPE gender AS ENUM ('male', 'female', 'other');
            
            -- Add the column
            ALTER TABLE users 
            ADD COLUMN gender gender;
        END IF;
    END $$;
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(alter_table_sql))
            connection.commit()
            print("Successfully added gender column to users table")
            
            # Now populate existing users with random gender values
            populate_existing_users(connection)
            
    except Exception as e:
        print(f"Error adding gender column: {e}")
        return False
    
    return True

def populate_existing_users(connection):
    """Populate existing users with random gender values"""
    
    # Get all users without gender
    result = connection.execute(text("SELECT id, full_name FROM users WHERE gender IS NULL"))
    users = result.fetchall()
    
    if not users:
        print("No users found without gender values")
        return
    
    print(f"Found {len(users)} users without gender values. Assigning random values...")
    
    genders = ['male', 'female', 'other']
    
    for user in users:
        user_id, full_name = user
        
        # Assign gender based on name patterns (simple heuristic) or random
        assigned_gender = assign_gender_by_name(full_name)
        
        # Update the user
        connection.execute(
            text("UPDATE users SET gender = :gender WHERE id = :user_id"),
            {"gender": assigned_gender, "user_id": user_id}
        )
        
        print(f"Assigned gender '{assigned_gender}' to user: {full_name}")
    
    connection.commit()
    print(f"Successfully assigned gender values to {len(users)} users")

def assign_gender_by_name(full_name):
    """Simple heuristic to assign gender based on name patterns"""
    
    # Common male name patterns/endings
    male_patterns = [
        'john', 'james', 'robert', 'michael', 'william', 'david', 'richard', 'joseph',
        'thomas', 'christopher', 'charles', 'daniel', 'matthew', 'anthony', 'mark',
        'donald', 'steven', 'paul', 'andrew', 'joshua', 'kenneth', 'kevin', 'brian',
        'george', 'edward', 'ronald', 'timothy', 'jason', 'jeffrey', 'ryan', 'jacob'
    ]
    
    # Common female name patterns/endings
    female_patterns = [
        'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
        'jessica', 'sarah', 'karen', 'nancy', 'lisa', 'betty', 'helen', 'sandra',
        'donna', 'carol', 'ruth', 'sharon', 'michelle', 'laura', 'sarah', 'kimberly',
        'deborah', 'dorothy', 'lisa', 'nancy', 'karen', 'betty', 'helen', 'sandra'
    ]
    
    name_lower = full_name.lower()
    first_name = name_lower.split()[0] if name_lower.split() else name_lower
    
    # Check for male patterns
    for pattern in male_patterns:
        if pattern in first_name:
            return 'male'
    
    # Check for female patterns
    for pattern in female_patterns:
        if pattern in first_name:
            return 'female'
    
    # Check for common endings
    if first_name.endswith(('a', 'ia', 'ina', 'lyn', 'lynn', 'elle', 'ette')):
        return 'female'
    elif first_name.endswith(('son', 'ton', 'er', 'ard', 'ert')):
        return 'male'
    
    # If no pattern matches, assign randomly with weighted distribution
    # 45% male, 45% female, 10% other
    rand = random.random()
    if rand < 0.45:
        return 'male'
    elif rand < 0.90:
        return 'female'
    else:
        return 'other'

if __name__ == "__main__":
    print("Adding gender column to users table...")
    success = add_gender_column()
    
    if success:
        print("Gender column addition and population completed successfully!")
    else:
        print("Gender column addition failed!")
        sys.exit(1)