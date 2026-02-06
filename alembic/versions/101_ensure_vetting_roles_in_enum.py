"""Ensure VETTING_APPROVER and VETTING_COMMITTEE are in roletype enum

Revision ID: 101_ensure_vetting_roles
Revises: 100_add_vetting_roles
Create Date: 2025-02-06 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '101_ensure_vetting_roles'
down_revision = '100_add_vetting_roles'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure VETTING_APPROVER and VETTING_COMMITTEE exist in roletype enum
    # Using IF NOT EXISTS to make this idempotent
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'")
    op.execute("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'")


def downgrade():
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type to remove values
    pass
