"""comprehensive fixes

Revision ID: comprehensive_fixes
Revises: 
Create Date: 2025-01-27 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'comprehensive_fixes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Fix events table - add missing columns
    op.add_column('events', sa.Column('event_type', sa.String(100), nullable=True))
    op.add_column('events', sa.Column('status', sa.String(50), nullable=True, default='Draft'))
    op.add_column('events', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('events', sa.Column('latitude', sa.Numeric(10,8), nullable=True))
    op.add_column('events', sa.Column('longitude', sa.Numeric(11,8), nullable=True))
    op.add_column('events', sa.Column('banner_image', sa.String(500), nullable=True))
    op.add_column('events', sa.Column('agenda_document_url', sa.String(500), nullable=True))
    op.add_column('events', sa.Column('registration_deadline', sa.Date(), nullable=True))
    op.add_column('events', sa.Column('vendor_accommodation_id', sa.Integer(), nullable=True))

    # Fix event_participants table - add missing columns
    op.add_column('event_participants', sa.Column('country', sa.String(100), nullable=True))
    op.add_column('event_participants', sa.Column('position', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('project', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('gender', sa.String(50), nullable=True))
    op.add_column('event_participants', sa.Column('eta', sa.String(255), nullable=True))
    op.add_column('event_participants', sa.Column('requires_eta', sa.Boolean(), nullable=True, default=False))
    op.add_column('event_participants', sa.Column('passport_document', sa.String(500), nullable=True))
    op.add_column('event_participants', sa.Column('ticket_document', sa.String(500), nullable=True))

    # Fix vendor_accommodations table - add missing columns
    op.add_column('vendor_accommodations', sa.Column('latitude', sa.String(20), nullable=True))
    op.add_column('vendor_accommodations', sa.Column('longitude', sa.String(20), nullable=True))
    op.add_column('vendor_accommodations', sa.Column('single_rooms', sa.Integer(), nullable=True, default=0))
    op.add_column('vendor_accommodations', sa.Column('double_rooms', sa.Integer(), nullable=True, default=0))

def downgrade() -> None:
    # Reverse all changes
    op.drop_column('vendor_accommodations', 'double_rooms')
    op.drop_column('vendor_accommodations', 'single_rooms')
    op.drop_column('vendor_accommodations', 'longitude')
    op.drop_column('vendor_accommodations', 'latitude')
    
    op.drop_column('event_participants', 'ticket_document')
    op.drop_column('event_participants', 'passport_document')
    op.drop_column('event_participants', 'requires_eta')
    op.drop_column('event_participants', 'eta')
    op.drop_column('event_participants', 'gender')
    op.drop_column('event_participants', 'project')
    op.drop_column('event_participants', 'position')
    op.drop_column('event_participants', 'country')
    
    op.drop_column('events', 'vendor_accommodation_id')
    op.drop_column('events', 'registration_deadline')
    op.drop_column('events', 'agenda_document_url')
    op.drop_column('events', 'banner_image')
    op.drop_column('events', 'longitude')
    op.drop_column('events', 'latitude')
    op.drop_column('events', 'country')
    op.drop_column('events', 'address')
    op.drop_column('events', 'status')
    op.drop_column('events', 'event_type')