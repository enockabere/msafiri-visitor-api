"""Merge multiple migration heads

Revision ID: merge_heads_2024_12_08
Revises: merge_transport_heads_001, passport_records_001, create_itinerary_reminders
Create Date: 2024-12-08 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_2024_12_08'
down_revision = ('merge_transport_heads_001', 'passport_records_001', 'create_itinerary_reminders')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no schema changes needed
    pass


def downgrade():
    # This is a merge migration - no schema changes needed
    pass
