"""Merge event voucher scanners and voucher invitations

Revision ID: merge_event_voucher_scanners
Revises: create_event_voucher_scanners, merge_voucher_invitations
Create Date: 2024-12-19 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_event_voucher_scanners'
down_revision = ('create_event_voucher_scanners', 'merge_voucher_invitations')
branch_labels = None
depends_on = None


def upgrade():
    """Merge migration - no changes needed"""
    pass


def downgrade():
    """Merge migration - no changes needed"""
    pass