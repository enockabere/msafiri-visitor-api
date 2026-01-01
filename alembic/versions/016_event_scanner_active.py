"""Add is_active column to event_voucher_scanners table

Revision ID: 016_event_scanner_active
Revises: 015_default_transport_providers
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016_event_scanner_active'
down_revision = '015_default_transport_providers'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_active column to event_voucher_scanners table
    op.add_column('event_voucher_scanners', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    # Remove is_active column from event_voucher_scanners table
    op.drop_column('event_voucher_scanners', 'is_active')