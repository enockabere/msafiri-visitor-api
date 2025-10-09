#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    """Add missing updated_at column to transport_status_updates"""
    
    # Read the SQL file
    with open('add_transport_updated_at.sql', 'r') as f:
        sql_content = f.read()
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Split SQL content by semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for statement in statements:
                print(f"Executing: {statement}")
                connection.execute(text(statement))
                connection.commit()
            
            print("Transport updated_at column added successfully!")
            
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration()