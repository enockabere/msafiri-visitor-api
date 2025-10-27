#!/usr/bin/env python3

import psycopg2
from app.core.config import settings

def fix_feedback_enum():
    """Fix the feedback category enum in the database"""
    
    # Connect to database
    conn = psycopg2.connect(
        host=settings.POSTGRES_SERVER,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        port=settings.POSTGRES_PORT
    )
    
    try:
        with conn.cursor() as cur:
            # Check current enum values
            print("🔍 Checking current enum values...")
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'feedbackcategory'
                )
                ORDER BY enumsortorder;
            """)
            
            current_values = [row[0] for row in cur.fetchall()]
            print(f"Current enum values: {current_values}")
            
            # Expected lowercase values
            expected_values = [
                'user_experience', 'performance', 'features', 
                'bug_report', 'suggestion', 'general'
            ]
            
            if set(current_values) == set(expected_values):
                print("✅ Enum values are correct!")
                return
            
            print("❌ Enum values need to be fixed")
            
            # Drop and recreate the enum
            print("🔧 Dropping existing enum...")
            
            # First, drop the constraint and column
            cur.execute("ALTER TABLE app_feedback DROP COLUMN IF EXISTS category;")
            cur.execute("DROP TYPE IF EXISTS feedbackcategory CASCADE;")
            
            # Recreate the enum with correct values
            print("🔧 Creating new enum with correct values...")
            cur.execute("""
                CREATE TYPE feedbackcategory AS ENUM (
                    'user_experience', 'performance', 'features', 
                    'bug_report', 'suggestion', 'general'
                );
            """)
            
            # Add the column back
            cur.execute("""
                ALTER TABLE app_feedback 
                ADD COLUMN category feedbackcategory NOT NULL DEFAULT 'general';
            """)
            
            # Create index
            cur.execute("CREATE INDEX ix_app_feedback_category ON app_feedback (category);")
            
            conn.commit()
            print("✅ Enum fixed successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_feedback_enum()