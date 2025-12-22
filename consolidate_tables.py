#!/usr/bin/env python3
"""
Script to consolidate participant data into single table
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/msafiri_db')

def consolidate_tables():
    """Add fields to event_participants table and migrate data"""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Starting table consolidation...")
        
        # Add missing fields to event_participants table
        fields_to_add = [
            "first_name VARCHAR(255)",
            "last_name VARCHAR(255)", 
            "oc VARCHAR(50)",
            "contract_status VARCHAR(100)",
            "contract_type VARCHAR(100)",
            "gender_identity VARCHAR(100)",
            "sex VARCHAR(50)",
            "pronouns VARCHAR(50)",
            "current_position VARCHAR(255)",
            "country_of_work VARCHAR(255)",
            "project_of_work VARCHAR(255)",
            "personal_email VARCHAR(255)",
            "msf_email VARCHAR(255)",
            "hrco_email VARCHAR(255)",
            "career_manager_email VARCHAR(255)",
            "ld_manager_email VARCHAR(255)",
            "line_manager_email VARCHAR(255)",
            "phone_number VARCHAR(50)",
            "travelling_internationally VARCHAR(10)",
            "accommodation_needs TEXT",
            "daily_meals VARCHAR(255)",
            "certificate_name VARCHAR(255)",
            "badge_name VARCHAR(255)",
            "motivation_letter TEXT",
            "code_of_conduct_confirm VARCHAR(10)",
            "travel_requirements_confirm VARCHAR(10)"
        ]
        
        print("Adding fields to event_participants table...")
        for field in fields_to_add:
            field_name = field.split()[0]
            try:
                db.execute(text(f"ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS {field}"))
                print(f"   Added field: {field_name}")
            except Exception as e:
                print(f"   Field {field_name} already exists or error: {e}")
        
        db.commit()
        print("All fields added successfully!")
        
        # Check if public_registrations table exists and has data
        try:
            count = db.execute(text("SELECT COUNT(*) FROM public_registrations")).scalar()
            print(f"Found {count} records in public_registrations table")
            
            if count > 0:
                print("Migrating data from public_registrations to event_participants...")
                
                # Update event_participants with data from public_registrations
                db.execute(text("""
                    UPDATE event_participants ep
                    SET 
                        first_name = pr.first_name,
                        last_name = pr.last_name,
                        oc = pr.oc,
                        contract_status = pr.contract_status,
                        contract_type = pr.contract_type,
                        gender_identity = pr.gender_identity,
                        sex = pr.sex,
                        pronouns = pr.pronouns,
                        current_position = pr.current_position,
                        country_of_work = pr.country_of_work,
                        project_of_work = pr.project_of_work,
                        personal_email = pr.personal_email,
                        msf_email = pr.msf_email,
                        hrco_email = pr.hrco_email,
                        career_manager_email = pr.career_manager_email,
                        ld_manager_email = pr.ld_manager_email,
                        line_manager_email = pr.line_manager_email,
                        phone_number = pr.phone_number,
                        travelling_internationally = pr.travelling_internationally,
                        accommodation_needs = pr.accommodation_needs,
                        daily_meals = pr.daily_meals,
                        certificate_name = pr.certificate_name,
                        badge_name = pr.badge_name,
                        motivation_letter = pr.motivation_letter,
                        code_of_conduct_confirm = pr.code_of_conduct_confirm,
                        travel_requirements_confirm = pr.travel_requirements_confirm
                    FROM public_registrations pr
                    WHERE ep.id = pr.participant_id
                """))
                
                db.commit()
                print("Data migration completed!")
                
                # Verify migration
                updated_count = db.execute(text("""
                    SELECT COUNT(*) FROM event_participants 
                    WHERE first_name IS NOT NULL OR personal_email IS NOT NULL
                """)).scalar()
                print(f"Verified: {updated_count} participants now have consolidated data")
        
        except Exception as e:
            print(f"No public_registrations table found or error: {e}")
        
        print("Table consolidation completed successfully!")
        
    except Exception as e:
        print(f"Error during consolidation: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    consolidate_tables()