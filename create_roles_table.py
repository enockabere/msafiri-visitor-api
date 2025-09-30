#!/usr/bin/env python3
"""
Create roles table and add default roles
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_roles_table():
    """Create roles table and add default roles"""
    try:
        with engine.connect() as conn:
            # Create roles table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    tenant_id VARCHAR NOT NULL REFERENCES tenants(slug),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create index
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_roles_tenant_id ON roles(tenant_id)
            """))
            
            conn.commit()
            print("Roles table created successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating roles table: {e}")
        return False

def add_default_roles(tenant_slug: str):
    """Add default roles for a tenant"""
    default_roles = [
        ("HR Admin", "Human Resources Administrator"),
        ("Movement Travel Admin", "Movement and Travel Administrator"),
        ("Event Organizer", "Event Organization Administrator"),
        ("Service Provider", "Service Provider Administrator")
    ]
    
    try:
        with engine.connect() as conn:
            for role_name, description in default_roles:
                # Check if role already exists
                result = conn.execute(text("""
                    SELECT id FROM roles 
                    WHERE name = :name AND tenant_id = :tenant_id
                """), {"name": role_name, "tenant_id": tenant_slug})
                
                if not result.fetchone():
                    conn.execute(text("""
                        INSERT INTO roles (name, description, tenant_id, created_by)
                        VALUES (:name, :description, :tenant_id, 'system')
                    """), {
                        "name": role_name,
                        "description": description,
                        "tenant_id": tenant_slug
                    })
            
            conn.commit()
            print(f"Default roles added for tenant: {tenant_slug}")
            return True
            
    except Exception as e:
        print(f"Error adding default roles: {e}")
        return False

if __name__ == "__main__":
    success = create_roles_table()
    if success and len(sys.argv) > 1:
        tenant_slug = sys.argv[1]
        add_default_roles(tenant_slug)
    sys.exit(0 if success else 1)