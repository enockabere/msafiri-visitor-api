"""Fix vetting enum values

Revision ID: 039_fix_vetting_enum_values
Revises: 038_fix_perdiem_enum_values
Create Date: 2025-01-20 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '039_fix_vetting_enum_values'
down_revision = '038_fix_perdiem_enum_values'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing vetting roles to the roletype enum if they don't exist
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")

def downgrade():
    # Cannot remove enum values in PostgreSQL easily
    pass