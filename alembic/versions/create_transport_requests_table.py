"""Create transport_requests table

Revision ID: create_transport_requests
Revises: add_destination_field_to_flight_itineraries
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'create_transport_requests'
down_revision = None  # Will be set to current head
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'transport_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pickup_address', sa.String(500), nullable=False),
        sa.Column('pickup_latitude', sa.Float(), nullable=True),
        sa.Column('pickup_longitude', sa.Float(), nullable=True),
        sa.Column('dropoff_address', sa.String(500), nullable=False),
        sa.Column('dropoff_latitude', sa.Float(), nullable=True),
        sa.Column('dropoff_longitude', sa.Float(), nullable=True),
        sa.Column('pickup_time', sa.DateTime(), nullable=False),
        sa.Column('passenger_name', sa.String(255), nullable=False),
        sa.Column('passenger_phone', sa.String(50), nullable=False),
        sa.Column('passenger_email', sa.String(255), nullable=True),
        sa.Column('vehicle_type', sa.String(100), nullable=True),
        sa.Column('flight_details', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('flight_itinerary_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.ForeignKeyConstraint(['flight_itinerary_id'], ['flight_itineraries.id'])
    )

def downgrade():
    op.drop_table('transport_requests')