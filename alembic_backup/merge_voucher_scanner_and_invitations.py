"""Merge voucher scanner and invitations heads

Revision ID: merge_voucher_invitations
Revises: add_voucher_scanner_role, create_invitations_table
Create Date: 2024-11-11 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_voucher_invitations'
down_revision = ('add_voucher_scanner_role', 'create_invitations_table')
branch_labels = None
depends_on = None

def upgrade():
    # This is a merge migration - no changes needed
    pass

def downgrade():
    # This is a merge migration - no changes needed
    pass