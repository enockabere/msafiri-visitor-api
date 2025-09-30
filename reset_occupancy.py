#!/usr/bin/env python3
"""
Script to reset all room and vendor accommodation occupancy counts to zero
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/msafiri_db")

def reset_occupancy_counts():
    """Reset all occupancy counts to zero"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Reset room occupancy counts
        rooms_result = db.execute(text("UPDATE rooms SET current_occupants = 0"))
        print(f"Reset occupancy for {rooms_result.rowcount} rooms")
        
        # Reset vendor accommodation occupancy counts
        vendor_result = db.execute(text("UPDATE vendor_accommodations SET current_occupants = 0"))
        print(f"Reset occupancy for {vendor_result.rowcount} vendor accommodations")
        
        # Reset guesthouse occupied_rooms count
        gh_result = db.execute(text("UPDATE guesthouses SET occupied_rooms = 0"))
        print(f"Reset occupied_rooms for {gh_result.rowcount} guesthouses")
        
        db.commit()
        print("Successfully reset all occupancy counts")
        
    except Exception as e:
        print(f"Error resetting occupancy: {e}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    reset_occupancy_counts()