"""add pickup_location to flight_itineraries

Revision ID: add_pickup_location
Revises: 148b242d4e59
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_pickup_location'
down_revision = '148b242d4e59'
branch_labels = None
depends_on = None


def upgrade():
    # Add pickup_location column
    op.add_column('flight_itineraries', sa.Column('pickup_location', sa.String(255), nullable=True))
    
    # Make arrival_airport nullable
    op.alter_column('flight_itineraries', 'arrival_airport', nullable=True)
    
    # Make arrival_date nullable
    op.alter_column('flight_itineraries', 'arrival_date', nullable=True)


def downgrade():
    # Remove pickup_location column
    op.drop_column('flight_itineraries', 'pickup_location')
    
    # Make arrival_airport not nullable again
    op.alter_column('flight_itineraries', 'arrival_airport', nullable=False)
    
    # Make arrival_date not nullable again
    op.alter_column('flight_itineraries', 'arrival_date', nullable=False)