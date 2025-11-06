"""add destination field to flight_itineraries

Revision ID: add_destination_field
Revises: add_pickup_location
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_destination_field'
down_revision = 'add_pickup_location'
branch_labels = None
depends_on = None


def upgrade():
    # Add destination column
    op.add_column('flight_itineraries', sa.Column('destination', sa.String(255), nullable=True))


def downgrade():
    # Remove destination column
    op.drop_column('flight_itineraries', 'destination')