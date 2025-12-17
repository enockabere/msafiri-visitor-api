"""Add pickup_confirmed field to flight_itineraries

Revision ID: add_pickup_confirmed
Revises: add_destination_field
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pickup_confirmed'
down_revision = 'add_destination_field'
branch_labels = None
depends_on = None

def upgrade():
    # Add pickup_confirmed column to flight_itineraries table
    op.add_column('flight_itineraries', sa.Column('pickup_confirmed', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    # Remove pickup_confirmed column from flight_itineraries table
    op.drop_column('flight_itineraries', 'pickup_confirmed')