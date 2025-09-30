#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    """Fix transport booking enum constraints with uppercase values"""
    
    # Read the SQL file
    with open('fix_transport_enums_uppercase.sql', 'r') as f:
        sql_content = f.read()
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Split SQL content by semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for statement in statements:
                print(f"Executing: {statement[:80]}...")
                connection.execute(text(statement))
                connection.commit()
            
            print("Transport enum constraints fixed with uppercase values!")
            
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    run_migration()