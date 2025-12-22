#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def run_sql_migration():
    """Run the SQL migration to change registration_deadline to timestamp"""
    try:
        print("Connecting to database...")
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            print("Connected to database")
            
            # Read the SQL file
            sql_file = os.path.join(os.path.dirname(__file__), 'change_registration_deadline_to_timestamp.sql')
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            trans = conn.begin()
            try:
                for i, statement in enumerate(statements, 1):
                    print(f"Executing statement {i}/{len(statements)}: {statement[:50]}...")
                    conn.execute(text(statement))
                
                trans.commit()
                print("Migration completed successfully!")
                
                # Verify the change
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'events' AND column_name = 'registration_deadline'
                """))
                
                row = result.fetchone()
                if row:
                    print(f"Column info: {row.column_name} - {row.data_type} - nullable: {row.is_nullable}")
                else:
                    print("Could not verify column info")
                    
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_sql_migration()
    sys.exit(0 if success else 1)