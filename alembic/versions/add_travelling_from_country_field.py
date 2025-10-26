"""Add travelling_from_country to event_participants

Revision ID: add_travelling_from_country
Revises: f1a2b3c4d5e6
Create Date: 2025-01-22 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_travelling_from_country'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade():
    # Add travelling_from_country column to event_participants table
    op.add_column('event_participants', sa.Column('travelling_from_country', sa.String(length=100), nullable=True))

def downgrade():
    # Remove travelling_from_country column from event_participants table
    op.drop_column('event_participants', 'travelling_from_country')