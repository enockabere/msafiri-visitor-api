#!/usr/bin/env python3
"""
Robust database deletion script for participants and related data
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://postgres:admin@localhost:5432/msafiri_db"

def delete_all_participants():
    """Delete all participants and related data directly from database"""
    
    print("STARTING DELETION OF ALL PARTICIPANTS AND RELATED DATA")
    
    try:
        # Create database connection
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Tables to clean in order (to avoid foreign key constraints)
        tables_to_clean = [
            "line_manager_recommendations",
            "form_responses", 
            "accommodation_allocations",
            "participant_qr_codes",
            "public_registrations",
            "event_participants"
        ]
        
        total_deleted = 0
        results = []
        
        for table in tables_to_clean:
            # Create a new session for each table to handle transaction errors
            db = SessionLocal()
            try:
                # Check if table exists first
                table_exists = db.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """), {"table_name": table}).scalar()
                
                if not table_exists:
                    results.append(f"Table {table} does not exist - skipping")
                    print(f"Table {table} does not exist - skipping")
                    db.close()
                    continue
                
                # Get count first
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                
                if count > 0:
                    print(f"Deleting {count} records from {table}...")
                    db.execute(text(f"DELETE FROM {table}"))
                    db.commit()
                    total_deleted += count
                    results.append(f"Deleted {count} records from {table}")
                    print(f"Deleted {count} records from {table}")
                else:
                    results.append(f"No records found in {table}")
                    print(f"No records found in {table}")
                    
            except Exception as e:
                db.rollback()
                error_msg = f"Could not clean {table}: {e}"
                results.append(error_msg)
                print(f"ERROR: {error_msg}")
            finally:
                db.close()
        
        print(f"\nDELETION COMPLETE! Total records deleted: {total_deleted}")
        print("\nSummary:")
        for result in results:
            print(f"   - {result}")
        
        return {
            "success": True,
            "total_deleted": total_deleted,
            "details": results
        }
        
    except Exception as e:
        print(f"ERROR during deletion: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = delete_all_participants()
    if result["success"]:
        print(f"\nSuccessfully deleted {result['total_deleted']} records")
    else:
        print(f"\nDeletion failed: {result['error']}")
        sys.exit(1)