#!/usr/bin/env python3
"""
Script to delete all participants and related data from the database.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def delete_all_participants():
    """Delete all participants and related data."""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        try:
            print("Starting participant deletion...")
            
            # Delete in order to respect foreign key constraints
            tables_to_clear = [
                'form_responses',
                'line_manager_recommendations', 
                'event_participants'
            ]
            
            for table in tables_to_clear:
                result = db.execute(text(f"DELETE FROM {table}"))
                print(f"Deleted {result.rowcount} records from {table}")
            
            db.commit()
            print("All participants and related data deleted successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"Error deleting participants: {e}")
            raise

if __name__ == "__main__":
    delete_all_participants()