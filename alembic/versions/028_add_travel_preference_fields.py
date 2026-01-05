"""Add travel preference fields to event_participants

Revision ID: 028_add_travel_preference_fields
Revises: a24c6988176d
Create Date: 2024-01-05 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '028_add_travel_preference_fields'
down_revision = 'a24c6988176d'
branch_labels = None
depends_on = None

def upgrade():
    # Add new travel preference fields to event_participants table
    op.add_column('event_participants', sa.Column('accommodation_preference', sa.String(100), nullable=True))
    op.add_column('event_participants', sa.Column('has_dietary_requirements', sa.Boolean(), default=False, nullable=True))
    op.add_column('event_participants', sa.Column('has_accommodation_needs', sa.Boolean(), default=False, nullable=True))

def downgrade():
    # Remove the added columns
    op.drop_column('event_participants', 'has_accommodation_needs')
    op.drop_column('event_participants', 'has_dietary_requirements')
    op.drop_column('event_participants', 'accommodation_preference')