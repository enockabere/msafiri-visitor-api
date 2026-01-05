#!/usr/bin/env python3
"""
Fix vetting status standardization
Ensures all vetting committee statuses use only: open, pending_approval, approved
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def fix_vetting_statuses():
    """Fix any non-standard vetting statuses in the database"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("Checking vetting committee statuses...")
        
        # Check current status values
        result = db.execute(text("""
            SELECT DISTINCT status FROM vetting_committees
        """)).fetchall()
        
        current_statuses = [row[0] for row in result]
        print(f"Current statuses in database: {current_statuses}")
        
        # Standardize any non-standard statuses
        updates_made = 0
        
        # Map any variations to standard values
        status_mappings = {
            'pending': 'open',
            'submitted': 'pending_approval',
            'submitted_for_approval': 'pending_approval',
            'SUBMITTED_FOR_APPROVAL': 'pending_approval',
            'PENDING_APPROVAL': 'pending_approval',
            'APPROVED': 'approved',
            'OPEN': 'open'
        }
        
        for old_status, new_status in status_mappings.items():
            if old_status in current_statuses:
                print(f"Updating '{old_status}' to '{new_status}'...")
                
                result = db.execute(text("""
                    UPDATE vetting_committees 
                    SET status = :new_status 
                    WHERE status = :old_status
                """), {"new_status": new_status, "old_status": old_status})
                
                updated_count = result.rowcount
                if updated_count > 0:
                    updates_made += updated_count
                    print(f"   Updated {updated_count} records")
        
        # Commit changes
        if updates_made > 0:
            db.commit()
            print(f"\nSuccessfully standardized {updates_made} vetting status records")
        else:
            print("\nAll vetting statuses are already standardized")
        
        # Verify final state
        result = db.execute(text("""
            SELECT DISTINCT status FROM vetting_committees
        """)).fetchall()
        
        final_statuses = [row[0] for row in result]
        print(f"Final statuses in database: {final_statuses}")
        
        # Check if all statuses are now standard
        standard_statuses = {'open', 'pending_approval', 'approved'}
        non_standard = set(final_statuses) - standard_statuses
        
        if non_standard:
            print(f"Warning: Non-standard statuses still exist: {non_standard}")
        else:
            print("All statuses are now standardized!")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_vetting_statuses()