#!/usr/bin/env python3
"""
Direct script to delete all visitor accommodation allocations
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL - adjust as needed
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/msafiri_db")

def delete_all_allocations():
    """Delete all accommodation allocations directly"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Get count before deletion
        count_result = db.execute(text("SELECT COUNT(*) FROM accommodation_allocations"))
        count = count_result.scalar()
        print(f"Found {count} accommodation allocations to delete")
        
        if count == 0:
            print("No allocations to delete")
            return
        
        # Delete all allocations
        result = db.execute(text("DELETE FROM accommodation_allocations"))
        db.commit()
        
        print(f"Successfully deleted {result.rowcount} accommodation allocations")
        
    except Exception as e:
        print(f"Error deleting allocations: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    delete_all_allocations()