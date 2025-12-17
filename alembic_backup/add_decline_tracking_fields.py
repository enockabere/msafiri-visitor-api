"""Add decline tracking fields to event_participants

Revision ID: add_decline_tracking_fields
Revises: create_transport_requests
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_decline_tracking_fields'
down_revision = 'create_transport_requests'
branch_labels = None
depends_on = None

def upgrade():
    # Add decline tracking fields to event_participants table
    op.add_column('event_participants', sa.Column('decline_reason', sa.Text(), nullable=True))
    op.add_column('event_participants', sa.Column('declined_at', sa.DateTime(), nullable=True))

def downgrade():
    # Remove decline tracking fields
    op.drop_column('event_participants', 'declined_at')
    op.drop_column('event_participants', 'decline_reason')