#!/usr/bin/env python3
"""
Add new fields to public_registrations table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def add_new_fields():
    """Add badge_name and motivation_letter fields to public_registrations table"""
    
    print("Adding new fields to public_registrations table...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Add badge_name field
            conn.execute(text("""
                ALTER TABLE public_registrations 
                ADD COLUMN IF NOT EXISTS badge_name VARCHAR(255)
            """))
            
            # Add motivation_letter field (rich text)
            conn.execute(text("""
                ALTER TABLE public_registrations 
                ADD COLUMN IF NOT EXISTS motivation_letter TEXT
            """))
            
            # Add email_checked field to track if email was validated
            conn.execute(text("""
                ALTER TABLE public_registrations 
                ADD COLUMN IF NOT EXISTS email_checked BOOLEAN DEFAULT FALSE
            """))
            
            # Add recommendation_requested field
            conn.execute(text("""
                ALTER TABLE public_registrations 
                ADD COLUMN IF NOT EXISTS recommendation_requested BOOLEAN DEFAULT FALSE
            """))
            
            conn.commit()
            print("✅ New fields added successfully")
            
        except Exception as e:
            print(f"❌ Error adding fields: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_new_fields()