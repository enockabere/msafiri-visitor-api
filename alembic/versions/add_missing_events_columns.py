"""add missing events columns

Revision ID: add_missing_events_columns
Revises: create_events_table
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_events_columns'
down_revision = 'create_events_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add missing columns to events table
    op.add_column('events', sa.Column('event_type', sa.String(100), nullable=True))
    op.add_column('events', sa.Column('status', sa.String(50), nullable=True, default='Draft'))
    op.add_column('events', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('events', sa.Column('latitude', sa.Numeric(10,8), nullable=True))
    op.add_column('events', sa.Column('longitude', sa.Numeric(11,8), nullable=True))
    op.add_column('events', sa.Column('banner_image', sa.String(500), nullable=True))
    op.add_column('events', sa.Column('agenda_document_url', sa.String(500), nullable=True))
    op.add_column('events', sa.Column('registration_deadline', sa.Date(), nullable=True))

def downgrade() -> None:
    # Remove the added columns
    op.drop_column('events', 'registration_deadline')
    op.drop_column('events', 'agenda_document_url')
    op.drop_column('events', 'banner_image')
    op.drop_column('events', 'longitude')
    op.drop_column('events', 'latitude')
    op.drop_column('events', 'country')
    op.drop_column('events', 'address')
    op.drop_column('events', 'status')
    op.drop_column('events', 'event_type')