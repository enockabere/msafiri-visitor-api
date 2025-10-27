#!/usr/bin/env python3

import psycopg2
from app.core.config import settings

def fix_enum_complete():
    """Completely recreate the feedback enum to fix the mismatch"""
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    
    try:
        with conn.cursor() as cur:
            print("🔧 Starting complete enum fix...")
            
            # Step 1: Check if app_feedback table exists and has data
            cur.execute("SELECT COUNT(*) FROM app_feedback;")
            feedback_count = cur.fetchone()[0]
            print(f"📊 Found {feedback_count} existing feedback records")
            
            # Step 2: Create backup of existing data if any
            if feedback_count > 0:
                print("💾 Creating backup of existing data...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS app_feedback_backup AS 
                    SELECT id, user_id, rating, category::text as category_text, 
                           feedback_text, created_at, updated_at 
                    FROM app_feedback;
                """)
            
            # Step 3: Drop the table and enum completely
            print("🗑️ Dropping table and enum...")
            cur.execute("DROP TABLE IF EXISTS app_feedback CASCADE;")
            cur.execute("DROP TYPE IF EXISTS feedbackcategory CASCADE;")
            
            # Step 4: Recreate the enum with correct values
            print("🔧 Creating new enum...")
            cur.execute("""
                CREATE TYPE feedbackcategory AS ENUM (
                    'user_experience', 
                    'performance', 
                    'features', 
                    'bug_report', 
                    'suggestion', 
                    'general'
                );
            """)
            
            # Step 5: Recreate the table
            print("🔧 Creating new table...")
            cur.execute("""
                CREATE TABLE app_feedback (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    rating INTEGER NOT NULL,
                    category feedbackcategory NOT NULL,
                    feedback_text TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                );
            """)
            
            # Step 6: Create indexes
            print("🔧 Creating indexes...")
            cur.execute("CREATE INDEX ix_app_feedback_user_id ON app_feedback (user_id);")
            cur.execute("CREATE INDEX ix_app_feedback_rating ON app_feedback (rating);")
            cur.execute("CREATE INDEX ix_app_feedback_category ON app_feedback (category);")
            
            # Step 7: Restore data if any existed
            if feedback_count > 0:
                print("📥 Restoring backup data...")
                cur.execute("""
                    INSERT INTO app_feedback (id, user_id, rating, category, feedback_text, created_at, updated_at)
                    SELECT id, user_id, rating, category_text::feedbackcategory, 
                           feedback_text, created_at, updated_at 
                    FROM app_feedback_backup;
                """)
                
                # Update sequence
                cur.execute("SELECT setval('app_feedback_id_seq', (SELECT MAX(id) FROM app_feedback));")
                
                # Drop backup table
                cur.execute("DROP TABLE app_feedback_backup;")
            
            conn.commit()
            print("✅ Enum fix completed successfully!")
            
            # Verify the fix
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'feedbackcategory')
                ORDER BY enumsortorder;
            """)
            values = [row[0] for row in cur.fetchall()]
            print(f"✅ Verified enum values: {values}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_enum_complete()