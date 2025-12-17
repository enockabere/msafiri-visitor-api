#!/usr/bin/env python3
"""
Script to run the vetting status migration
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db.database import SessionLocal
from sqlalchemy import text

def run_migration():
    """Run the vetting status migration"""
    
    try:
        db = SessionLocal()
        
        print("Running vetting status migration...")
        
        # Create new enum type
        db.execute(text("""
            DO $$ BEGIN
                CREATE TYPE vettingstatus_new AS ENUM ('open', 'pending_approval', 'approved');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Update existing records to map old values to new values
        db.execute(text("""
            UPDATE vetting_committees 
            SET status = CASE 
                WHEN status = 'pending' THEN 'open'
                WHEN status = 'in_progress' THEN 'open'
                WHEN status = 'submitted_for_approval' THEN 'pending_approval'
                WHEN status = 'completed' THEN 'approved'
                ELSE 'open'
            END::text
        """))
        
        # Alter column to use new enum
        db.execute(text("ALTER TABLE vetting_committees ALTER COLUMN status TYPE vettingstatus_new USING status::text::vettingstatus_new"))
        
        # Drop old enum
        db.execute(text("DROP TYPE IF EXISTS vettingstatus"))
        
        # Rename new enum to original name
        db.execute(text("ALTER TYPE vettingstatus_new RENAME TO vettingstatus"))
        
        db.commit()
        print("Migration completed successfully!")
        
        # Show updated records
        result = db.execute(text("SELECT id, status FROM vetting_committees")).fetchall()
        if result:
            print("\nUpdated committees:")
            for committee_id, status in result:
                print(f"  Committee {committee_id}: {status}")
        else:
            print("\nNo committees found in database")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    run_migration()