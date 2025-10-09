#!/usr/bin/env python3
"""
Add agenda_document_url column to events table
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def add_agenda_document_url_column():
    """Add agenda_document_url column to events table"""
    
    sql = """
    ALTER TABLE events 
    ADD COLUMN IF NOT EXISTS agenda_document_url VARCHAR(500);
    """
    
    try:
        with engine.connect() as conn:
            print("Adding agenda_document_url column to events table...")
            conn.execute(text(sql))
            conn.commit()
            print("Column added successfully!")
            return True
            
    except Exception as e:
        print(f"Error adding column: {e}")
        return False

if __name__ == "__main__":
    success = add_agenda_document_url_column()
    sys.exit(0 if success else 1)