#!/usr/bin/env python3
"""
Script to generate slugs for existing passport records
Run this after adding the slug column to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.passport_record import PassportRecord

def generate_slugs_for_existing_records():
    """Generate slugs for all passport records that don't have one"""
    
    db = next(get_db())
    
    try:
        # Get all passport records without slugs
        records_without_slugs = db.query(PassportRecord).filter(
            PassportRecord.slug.is_(None)
        ).all()
        
        print(f"Found {len(records_without_slugs)} passport records without slugs")
        
        updated_count = 0
        for record in records_without_slugs:
            try:
                # Generate slug using the model method
                record.generate_slug()
                updated_count += 1
                print(f"Generated slug for record ID {record.id}: {record.slug}")
            except Exception as e:
                print(f"Error generating slug for record ID {record.id}: {e}")
        
        # Commit all changes
        db.commit()
        print(f"Successfully generated slugs for {updated_count} records")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_slugs_for_existing_records()