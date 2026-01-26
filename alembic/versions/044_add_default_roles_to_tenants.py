"""Add default roles to all tenants

Revision ID: 044_add_default_roles_to_tenants
Revises: 043_replace_budget_account_code_with_new_fields
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '044_add_default_roles_to_tenants'
down_revision = '043_replace_budget_account_code_with_new_fields'
branch_labels = None
depends_on = None

def upgrade():
    """Add default roles to all existing tenants"""
    # Get database connection
    connection = op.get_bind()
    
    # Define default roles
    default_roles = [
        ("MT Admin", "Movement and Travel Administrator"),
        ("HR Admin", "Human Resources Administrator"), 
        ("Event Admin", "Event Administrator"),
        ("Finance Admin", "Finance Administrator"),
        ("Staff", "Staff Member"),
        ("Guest", "Guest User")
    ]
    
    # Get all existing tenants
    result = connection.execute(text("SELECT slug FROM tenants WHERE is_active = true"))
    tenants = result.fetchall()
    
    # Create default roles for each tenant
    for tenant in tenants:
        tenant_slug = tenant[0]
        
        for role_name, role_description in default_roles:
            # Check if role already exists
            existing = connection.execute(text("""
                SELECT id FROM roles 
                WHERE name = :name AND tenant_id = :tenant_id
            """), {"name": role_name, "tenant_id": tenant_slug}).fetchone()
            
            if not existing:
                # Insert the role
                connection.execute(text("""
                    INSERT INTO roles (name, description, tenant_id, is_active, created_by, created_at)
                    VALUES (:name, :description, :tenant_id, true, 'system', NOW())
                """), {
                    "name": role_name,
                    "description": role_description,
                    "tenant_id": tenant_slug
                })

def downgrade():
    """Remove system-created default roles"""
    connection = op.get_bind()
    
    # Remove roles created by system
    connection.execute(text("""
        DELETE FROM roles 
        WHERE created_by = 'system' 
        AND name IN ('MT Admin', 'HR Admin', 'Event Admin', 'Finance Admin', 'Staff', 'Guest')
    """))