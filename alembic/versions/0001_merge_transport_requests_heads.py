"""Merge multiple heads from create_transport_requests

Revision ID: merge_transport_heads_001
Revises: add_decline_tracking_fields, fix_chat_messages_cascade_delete, add_transport_driver_details
Create Date: 2024-12-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_transport_heads_001'
down_revision = ('add_decline_tracking_fields', 'fix_chat_messages_cascade_delete', 'add_transport_driver_details')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no schema changes needed
    pass


def downgrade():
    # This is a merge migration - no schema changes needed
    pass
