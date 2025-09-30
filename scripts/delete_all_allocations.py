#!/usr/bin/env python3
"""
Script to delete all visitor accommodation allocations
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.accommodation import AccommodationAllocation

def delete_all_allocations():
    """Delete all accommodation allocations"""
    db = next(get_db())
    try:
        # Get count before deletion
        count = db.query(AccommodationAllocation).count()
        print(f"Found {count} accommodation allocations to delete")
        
        if count == 0:
            print("No allocations to delete")
            return
        
        # Delete all allocations
        deleted = db.query(AccommodationAllocation).delete()
        db.commit()
        
        print(f"Successfully deleted {deleted} accommodation allocations")
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting allocations: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_allocations()