"""Merge inventory and remaining tables heads

Revision ID: merge_inv_remaining
Revises: create_invitations_table, create_inventory_table
Create Date: 2024-12-05 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_inv_remaining'
down_revision = ('create_invitations_table', 'create_inventory_table')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration, no changes needed
    pass


def downgrade():
    # This is a merge migration, no changes needed
    pass
