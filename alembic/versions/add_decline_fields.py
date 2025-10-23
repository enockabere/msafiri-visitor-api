"""Add decline fields to event_participants

Revision ID: add_decline_fields
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_decline_fields'
down_revision = None
depends_on = None

def upgrade():
    # Add decline_reason and declined_at columns to event_participants table
    op.add_column('event_participants', sa.Column('decline_reason', sa.Text(), nullable=True))
    op.add_column('event_participants', sa.Column('declined_at', sa.DateTime(), nullable=True))

def downgrade():
    # Remove decline_reason and declined_at columns
    op.drop_column('event_participants', 'declined_at')
    op.drop_column('event_participants', 'decline_reason')