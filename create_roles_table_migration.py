#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_roles_table():
    """Create roles table if it doesn't exist"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                print("🔄 Creating roles table...")
                
                # Create roles table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        tenant_id VARCHAR NOT NULL REFERENCES tenants(slug),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by VARCHAR(255),
                        updated_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create index on tenant_id
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON roles(tenant_id)
                """))
                
                # Create unique constraint on name + tenant_id
                connection.execute(text("""
                    ALTER TABLE roles 
                    ADD CONSTRAINT IF NOT EXISTS unique_role_name_per_tenant 
                    UNIQUE (name, tenant_id)
                """))
                
                print("✅ Roles table created successfully")
                
                # Commit transaction
                trans.commit()
                print("🎉 Migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {str(e)}")
                raise
                
    except SQLAlchemyError as e:
        print(f"❌ Database connection error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    create_roles_table()