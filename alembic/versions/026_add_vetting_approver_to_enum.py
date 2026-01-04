"""Add VETTING_APPROVER to roletype enum

Revision ID: 026_add_vetting_approver_to_enum
Revises: 025_add_vetting_committee_tables
Create Date: 2025-01-05 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '026_add_vetting_approver_to_enum'
down_revision = '025_add_vetting_committee_tables'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing vetting roles to the roletype enum if they don't exist
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")

def downgrade():
    # Cannot remove enum values in PostgreSQL easily
    pass