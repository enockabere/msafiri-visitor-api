#!/usr/bin/env python3
"""
Create tenant and default roles
"""
import sys
import os
sys.path.append('.')

from sqlalchemy import text
from app.db.database import engine

def create_tenant_and_roles():
    """Create tenant and default roles"""
    try:
        with engine.connect() as conn:
            # Create tenant first
            conn.execute(text("""
                INSERT INTO tenants (
                    name, slug, contact_email, description, is_active, 
                    allow_self_registration, require_admin_approval, created_at
                ) VALUES (
                    'MSF KENYA OCA OFFICE', 'ko-oca', 'maebaenock95@gmail.com',
                    'MSF KENYA OCA OFFICE', TRUE, FALSE, TRUE, NOW()
                ) ON CONFLICT (slug) DO NOTHING
            """))
            
            # Add default roles
            default_roles = [
                ("HR Admin", "Human Resources Administrator"),
                ("Movement Travel Admin", "Movement and Travel Administrator"),
                ("Event Organizer", "Event Organization Administrator"),
                ("Service Provider", "Service Provider Administrator")
            ]
            
            for role_name, description in default_roles:
                conn.execute(text("""
                    INSERT INTO roles (name, description, tenant_id, created_by, created_at)
                    VALUES (:name, :description, 'ko-oca', 'system', NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "name": role_name,
                    "description": description
                })
            
            conn.commit()
            print("Tenant and roles created successfully!")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = create_tenant_and_roles()
    sys.exit(0 if success else 1)