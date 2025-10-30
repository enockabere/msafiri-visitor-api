"""Create flight_itineraries table

Revision ID: flight_itineraries_001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'flight_itineraries_001'
down_revision = None
depends_on = None

def upgrade():
    # Create flight_itineraries table
    op.create_table(
        'flight_itineraries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('airline', sa.String(100), nullable=True),
        sa.Column('flight_number', sa.String(50), nullable=True),
        sa.Column('departure_airport', sa.String(100), nullable=False),
        sa.Column('arrival_airport', sa.String(100), nullable=False),
        sa.Column('departure_date', sa.DateTime(), nullable=False),
        sa.Column('arrival_date', sa.DateTime(), nullable=False),
        sa.Column('itinerary_type', sa.String(50), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=True, default=False),
        sa.Column('ticket_record_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('flight_itineraries')