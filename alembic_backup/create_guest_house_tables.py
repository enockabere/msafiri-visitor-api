"""Create guest house tables

Revision ID: create_guest_house_tables
Revises: add_travelling_from_country
Create Date: 2025-01-22 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_guest_house_tables'
down_revision = 'add_travelling_from_country'
branch_labels = None
depends_on = None

def upgrade():
    # Create guest_houses table
    op.create_table('guest_houses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=500), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('facilities', sa.JSON(), nullable=True),
        sa.Column('house_rules', sa.Text(), nullable=True),
        sa.Column('check_in_time', sa.String(length=10), nullable=True),
        sa.Column('check_out_time', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create guest_house_rooms table
    op.create_table('guest_house_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guest_house_id', sa.Integer(), nullable=False),
        sa.Column('room_number', sa.String(length=50), nullable=False),
        sa.Column('room_name', sa.String(length=255), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('room_type', sa.String(length=100), nullable=True),
        sa.Column('facilities', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['guest_house_id'], ['guest_houses.id'], ondelete='CASCADE')
    )
    
    # Create guest_house_bookings table
    op.create_table('guest_house_bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guest_house_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('check_in_date', sa.DateTime(), nullable=False),
        sa.Column('check_out_date', sa.DateTime(), nullable=False),
        sa.Column('number_of_guests', sa.Integer(), nullable=True, default=1),
        sa.Column('status', sa.String(length=50), nullable=True, default='booked'),
        sa.Column('checked_in', sa.Boolean(), nullable=True, default=False),
        sa.Column('checked_in_at', sa.DateTime(), nullable=True),
        sa.Column('checked_out', sa.Boolean(), nullable=True, default=False),
        sa.Column('checked_out_at', sa.DateTime(), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('booked_by', sa.String(length=255), nullable=False),
        sa.Column('booking_reference', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['guest_house_id'], ['guest_houses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['guest_house_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_guest_houses_id', 'guest_houses', ['id'])
    op.create_index('ix_guest_houses_tenant_id', 'guest_houses', ['tenant_id'])
    op.create_index('ix_guest_house_rooms_id', 'guest_house_rooms', ['id'])
    op.create_index('ix_guest_house_rooms_guest_house_id', 'guest_house_rooms', ['guest_house_id'])
    op.create_index('ix_guest_house_bookings_id', 'guest_house_bookings', ['id'])
    op.create_index('ix_guest_house_bookings_participant_id', 'guest_house_bookings', ['participant_id'])
    op.create_index('ix_guest_house_bookings_guest_house_id', 'guest_house_bookings', ['guest_house_id'])
    op.create_index('ix_guest_house_bookings_room_id', 'guest_house_bookings', ['room_id'])

def downgrade():
    # Drop indexes
    op.drop_index('ix_guest_house_bookings_room_id', 'guest_house_bookings')
    op.drop_index('ix_guest_house_bookings_guest_house_id', 'guest_house_bookings')
    op.drop_index('ix_guest_house_bookings_participant_id', 'guest_house_bookings')
    op.drop_index('ix_guest_house_bookings_id', 'guest_house_bookings')
    op.drop_index('ix_guest_house_rooms_guest_house_id', 'guest_house_rooms')
    op.drop_index('ix_guest_house_rooms_id', 'guest_house_rooms')
    op.drop_index('ix_guest_houses_tenant_id', 'guest_houses')
    op.drop_index('ix_guest_houses_id', 'guest_houses')
    
    # Drop tables
    op.drop_table('guest_house_bookings')
    op.drop_table('guest_house_rooms')
    op.drop_table('guest_houses')