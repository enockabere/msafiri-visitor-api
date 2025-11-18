#!/usr/bin/env python3
"""
Script to generate slugs for existing passport records
Run this after adding the slug column to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from app.core.config import settings
import hashlib
import secrets

def generate_slugs_for_existing_records():
    """Generate slugs for all passport records that don't have one"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        try:
            # Get all passport records without slugs
            result = connection.execute(text("""
                SELECT id, record_id, user_email 
                FROM passport_records 
                WHERE slug IS NULL
            """))
            
            records = result.fetchall()
            print(f"Found {len(records)} passport records without slugs")
            
            updated_count = 0
            for record in records:
                try:
                    # Generate slug
                    salt = secrets.token_hex(8)
                    data = f"{record.record_id}-{record.user_email}-{salt}"
                    slug = hashlib.sha256(data.encode()).hexdigest()[:16]
                    
                    # Update the record
                    connection.execute(text("""
                        UPDATE passport_records 
                        SET slug = :slug 
                        WHERE id = :record_id
                    """), {"slug": slug, "record_id": record.id})
                    
                    updated_count += 1
                    print(f"Generated slug for record ID {record.id}: {slug}")
                except Exception as e:
                    print(f"Error generating slug for record ID {record.id}: {e}")
            
            # Commit all changes
            connection.commit()
            print(f"Successfully generated slugs for {updated_count} records")
            
        except Exception as e:
            print(f"Error: {e}")
            connection.rollback()

if __name__ == "__main__":
    generate_slugs_for_existing_records()