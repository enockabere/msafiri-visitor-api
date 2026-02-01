"""Add accommodation_type to events table

Revision ID: 088_add_accommodation_type
Revises: 087_add_tenant_id
Create Date: 2026-02-01

This migration adds accommodation_type column to events table to specify
the type of accommodation: FullBoard, HalfBoard, BedAndBreakfast, BedOnly
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '088_add_accommodation_type'
down_revision = '087_add_tenant_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add accommodation_type column to events table
    op.add_column('events', sa.Column('accommodation_type', sa.String(50), nullable=True))


def downgrade():
    # Remove accommodation_type column from events table
    op.drop_column('events', 'accommodation_type')
