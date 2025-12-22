#!/usr/bin/env python3
"""
Script to force delete all participants from the database (no confirmation)
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

def delete_all_participants():
    """Delete all participants and related data"""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Starting participant deletion process...")
        
        # Get counts before deletion
        participant_count = db.execute(text("SELECT COUNT(*) FROM event_participants")).scalar()
        public_reg_count = db.execute(text("SELECT COUNT(*) FROM public_registrations")).scalar()
        form_responses_count = db.execute(text("SELECT COUNT(*) FROM form_responses")).scalar()
        line_manager_count = db.execute(text("SELECT COUNT(*) FROM line_manager_recommendations")).scalar()
        
        print(f"Current counts:")
        print(f"   - Event participants: {participant_count}")
        print(f"   - Public registrations: {public_reg_count}")
        print(f"   - Form responses: {form_responses_count}")
        print(f"   - Line manager recommendations: {line_manager_count}")
        
        if participant_count == 0 and public_reg_count == 0:
            print("No participants found. Database is already clean.")
            return
        
        # Delete in correct order to avoid foreign key constraints
        print("\nDeleting data...")
        
        # 1. Delete form responses first (references public_registrations)
        if form_responses_count > 0:
            db.execute(text("DELETE FROM form_responses"))
            print(f"   Deleted {form_responses_count} form responses")
        
        # 2. Delete line manager recommendations (references public_registrations)
        if line_manager_count > 0:
            db.execute(text("DELETE FROM line_manager_recommendations"))
            print(f"   Deleted {line_manager_count} line manager recommendations")
        
        # 3. Delete public registrations (references event_participants)
        if public_reg_count > 0:
            db.execute(text("DELETE FROM public_registrations"))
            print(f"   Deleted {public_reg_count} public registrations")
        
        # 4. Delete event participants (main table)
        if participant_count > 0:
            db.execute(text("DELETE FROM event_participants"))
            print(f"   Deleted {participant_count} event participants")
        
        # Reset auto-increment sequences
        print("\nResetting ID sequences...")
        db.execute(text("ALTER SEQUENCE event_participants_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE public_registrations_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE form_responses_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE line_manager_recommendations_id_seq RESTART WITH 1"))
        print("   ID sequences reset")
        
        # Commit all changes
        db.commit()
        
        print("\nAll participants deleted successfully!")
        print("Final verification:")
        
        # Verify deletion
        final_participant_count = db.execute(text("SELECT COUNT(*) FROM event_participants")).scalar()
        final_public_reg_count = db.execute(text("SELECT COUNT(*) FROM public_registrations")).scalar()
        final_form_responses_count = db.execute(text("SELECT COUNT(*) FROM form_responses")).scalar()
        final_line_manager_count = db.execute(text("SELECT COUNT(*) FROM line_manager_recommendations")).scalar()
        
        print(f"   - Event participants: {final_participant_count}")
        print(f"   - Public registrations: {final_public_reg_count}")
        print(f"   - Form responses: {final_form_responses_count}")
        print(f"   - Line manager recommendations: {final_line_manager_count}")
        
    except Exception as e:
        print(f"Error during deletion: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_participants()