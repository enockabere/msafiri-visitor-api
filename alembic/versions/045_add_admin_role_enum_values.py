"""Add admin role enum values

Revision ID: 045_add_admin_role_enum_values
Revises: 044_add_default_roles_to_tenants
Create Date: 2026-01-26 14:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '045_add_admin_role_enum_values'
down_revision = '044_add_default_roles_to_tenants'
branch_labels = None
depends_on = None

def upgrade():
    # Add new enum values to the roletype enum
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'FINANCE_ADMIN'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'HR_ADMIN'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'EVENT_ADMIN'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'MT_ADMIN'")

def downgrade():
    # Cannot remove enum values in PostgreSQL
    pass