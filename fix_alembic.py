#!/usr/bin/env python3
"""
Fix alembic revision cycle by creating a clean migration
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_database_url():
    return os.getenv('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/msafiri_db')

def fix_alembic():
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Fixing alembic revision cycle...")
        
        # Clear alembic version table to reset migration state
        db.execute(text("DELETE FROM alembic_version"))
        
        # Set to a stable revision (use the comprehensive initial migration)
        db.execute(text("INSERT INTO alembic_version (version_num) VALUES ('4c8f57e5312c')"))
        
        db.commit()
        print("Alembic version reset to stable revision")
        
        # Now add the missing fields directly
        fields_to_add = [
            ("first_name", "VARCHAR(255)"),
            ("last_name", "VARCHAR(255)"), 
            ("oc", "VARCHAR(50)"),
            ("contract_status", "VARCHAR(100)"),
            ("contract_type", "VARCHAR(100)"),
            ("gender_identity", "VARCHAR(100)"),
            ("sex", "VARCHAR(50)"),
            ("pronouns", "VARCHAR(50)"),
            ("current_position", "VARCHAR(255)"),
            ("country_of_work", "VARCHAR(255)"),
            ("project_of_work", "VARCHAR(255)"),
            ("personal_email", "VARCHAR(255)"),
            ("msf_email", "VARCHAR(255)"),
            ("hrco_email", "VARCHAR(255)"),
            ("career_manager_email", "VARCHAR(255)"),
            ("ld_manager_email", "VARCHAR(255)"),
            ("line_manager_email", "VARCHAR(255)"),
            ("phone_number", "VARCHAR(50)"),
            ("travelling_internationally", "VARCHAR(10)"),
            ("accommodation_needs", "TEXT"),
            ("daily_meals", "VARCHAR(255)"),
            ("certificate_name", "VARCHAR(255)"),
            ("badge_name", "VARCHAR(255)"),
            ("motivation_letter", "TEXT"),
            ("code_of_conduct_confirm", "VARCHAR(10)"),
            ("travel_requirements_confirm", "VARCHAR(10)")
        ]
        
        print("Adding missing fields to event_participants...")
        for field_name, field_type in fields_to_add:
            try:
                db.execute(text(f"ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS {field_name} {field_type}"))
                print(f"   Added: {field_name}")
            except Exception as e:
                print(f"   {field_name}: {e}")
        
        db.commit()
        print("Database schema updated successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_alembic()