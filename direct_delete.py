#!/usr/bin/env python3
"""
Direct database deletion script for participants and related data
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://msafiri_user:msafiri_password@41.90.240.229:5432/msafiri_db"

def delete_all_participants():
    """Delete all participants and related data directly from database"""
    
    print("🗑️  STARTING DELETION OF ALL PARTICIPANTS AND RELATED DATA")
    
    try:
        # Create database connection
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
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
            try:
                # Get count first
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                
                if count > 0:
                    print(f"🗑️  Deleting {count} records from {table}...")
                    db.execute(text(f"DELETE FROM {table}"))
                    total_deleted += count
                    results.append(f"Deleted {count} records from {table}")
                    print(f"✅ Deleted {count} records from {table}")
                else:
                    results.append(f"No records found in {table}")
                    print(f"ℹ️  No records found in {table}")
                    
            except Exception as e:
                error_msg = f"Could not clean {table}: {e}"
                results.append(error_msg)
                print(f"❌ ERROR: {error_msg}")
        
        # Commit all deletions
        db.commit()
        db.close()
        
        print(f"\\n🎉 DELETION COMPLETE! Total records deleted: {total_deleted}")
        print("\\n📋 Summary:")
        for result in results:
            print(f"   - {result}")
        
        return {
            "success": True,
            "total_deleted": total_deleted,
            "details": results
        }
        
    except Exception as e:
        print(f"❌ ERROR during deletion: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = delete_all_participants()
    if result["success"]:
        print(f"\\n✅ Successfully deleted {result['total_deleted']} records")
    else:
        print(f"\\n❌ Deletion failed: {result['error']}")
        sys.exit(1)