"""Add missing enum values to UserRole

Revision ID: add_missing_enum_values
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_missing_enum_values'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add missing enum values if they don't exist
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'APPROVER'")

def downgrade():
    # Cannot remove enum values in PostgreSQL
    pass