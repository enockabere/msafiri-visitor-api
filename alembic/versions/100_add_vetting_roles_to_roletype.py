"""Add VETTING_APPROVER and VETTING_COMMITTEE to roletype enum

Revision ID: 100_add_vetting_roles
Revises: 099_add_vetting_chat_tables
Create Date: 2025-02-06 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '100_add_vetting_roles'
down_revision = '099_add_vetting_chat_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add VETTING_APPROVER and VETTING_COMMITTEE to roletype enum if they don't exist
    # These values are required for the vetting committee functionality
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")

    # Also add to userrole enum if it exists
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")


def downgrade():
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type to remove values
    pass
