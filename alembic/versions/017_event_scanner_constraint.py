"""Add unique constraint to event_voucher_scanners table

Revision ID: 017_event_scanner_constraint
Revises: 016_event_scanner_active
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_event_scanner_constraint'
down_revision = '016_event_scanner_active'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint on (user_id, event_id) for ON CONFLICT clause
    op.create_unique_constraint('uq_event_voucher_scanners_user_event', 'event_voucher_scanners', ['user_id', 'event_id'])


def downgrade():
    # Remove unique constraint
    op.drop_constraint('uq_event_voucher_scanners_user_event', 'event_voucher_scanners', type_='unique')