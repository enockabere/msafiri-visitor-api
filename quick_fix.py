#!/usr/bin/env python3
"""Quick fix to add missing columns"""

from sqlalchemy import create_engine, text
from app.core.config import settings

def add_missing_columns():
    engine = create_engine(settings.DATABASE_URL)
    
    with open('add_missing_columns.sql', 'r') as f:
        sql_commands = f.read()
    
    with engine.connect() as conn:
        try:
            conn.execute(text(sql_commands))
            conn.commit()
            print("Missing columns added successfully")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_missing_columns()