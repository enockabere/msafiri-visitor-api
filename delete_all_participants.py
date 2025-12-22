#!/usr/bin/env python3
"""
Script to delete all participants and related data from the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def delete_all_participants():
    """Delete all participants and related data"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            print("Starting deletion of all participants and related data...")
            
            # Delete in correct order to avoid foreign key constraints
            tables_to_clean = [
                "line_manager_recommendations",
                "form_responses", 
                "accommodation_allocations",
                "participant_qr_codes",
                "event_participants"
            ]
            
            total_deleted = 0
            
            for table in tables_to_clean:
                try:
                    # Get count first
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    
                    if count > 0:
                        print(f"Deleting {count} records from {table}...")
                        conn.execute(text(f"DELETE FROM {table}"))
                        total_deleted += count
                        print(f"Deleted {count} records from {table}")
                    else:
                        print(f"No records found in {table}")
                        
                except Exception as e:
                    print(f"Could not clean {table}: {e}")
            
            # Commit all deletions
            conn.commit()
            
            print(f"\nDELETION COMPLETE!")
            print(f"Total records deleted: {total_deleted}")
            print(f"Database is now clean for new registrations")
            
        except Exception as e:
            print(f"ERROR during deletion: {e}")
            conn.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("WARNING: This will delete ALL participants and related data!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm == "DELETE ALL":
        success = delete_all_participants()
        if success:
            print("\nAll participants deleted successfully!")
        else:
            print("\nDeletion failed!")
    else:
        print("Deletion cancelled.")