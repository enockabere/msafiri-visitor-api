#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_useful_contacts_table():
    """Create the useful_contacts table"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL to create the table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS useful_contacts (
        id SERIAL PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        position VARCHAR NOT NULL,
        email VARCHAR NOT NULL,
        phone VARCHAR,
        department VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE,
        created_by VARCHAR NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_useful_contacts_tenant_id ON useful_contacts(tenant_id);
    """
    
    try:
        with engine.connect() as connection:
            # Execute the SQL
            connection.execute(text(create_table_sql))
            connection.commit()
            print("Successfully created useful_contacts table")
            
    except Exception as e:
        print(f"Error creating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating useful_contacts table...")
    success = create_useful_contacts_table()
    
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")
        sys.exit(1)