"""Create travel request tables

Revision ID: travel_requests_001
Revises: 068_add_approval_workflows
Create Date: 2024-02-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'travel_requests_001'
down_revision = '068_add_approval_workflows'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create travel_requests table
    op.create_table(
        'travel_requests',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('purpose', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('draft', 'pending_approval', 'approved', 'rejected', 'completed', name='travelrequeststatus'), default='draft', nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('approved_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('rejected_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
    )

    # Create travel_request_destinations table
    op.create_table(
        'travel_request_destinations',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('travel_request_id', sa.Integer, sa.ForeignKey('travel_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('origin', sa.String(255), nullable=False),
        sa.Column('destination', sa.String(255), nullable=False),
        sa.Column('departure_date', sa.Date, nullable=False),
        sa.Column('return_date', sa.Date, nullable=True),
        sa.Column('transport_mode', sa.Enum('flight', 'bus', 'train', 'car', 'other', name='transportmode'), default='flight', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('order', sa.Integer, default=0, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Create travel_request_messages table
    op.create_table(
        'travel_request_messages',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('travel_request_id', sa.Integer, sa.ForeignKey('travel_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sender_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sender_type', sa.Enum('user', 'admin', 'system', name='messagesendertype'), default='user', nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Create travel_request_documents table
    op.create_table(
        'travel_request_documents',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('travel_request_id', sa.Integer, sa.ForeignKey('travel_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('document_type', sa.Enum('ticket', 'itinerary', 'boarding_pass', 'other', name='documenttype'), default='ticket', nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_url', sa.String(1024), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('uploaded_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
    )

    # Create dependants table (user's family members)
    op.create_table(
        'dependants',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('relation_type', sa.Enum('spouse', 'child', 'parent', 'sibling', 'other', name='dependantrelationship'), nullable=False),
        sa.Column('date_of_birth', sa.Date, nullable=True),
        sa.Column('passport_number', sa.String(50), nullable=True),
        sa.Column('passport_expiry', sa.Date, nullable=True),
        sa.Column('nationality', sa.String(100), nullable=True),
        sa.Column('phone_number', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Create travel_request_travelers table (who is traveling)
    op.create_table(
        'travel_request_travelers',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('travel_request_id', sa.Integer, sa.ForeignKey('travel_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('traveler_type', sa.Enum('self', 'dependant', 'staff', name='travelertype'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('dependant_id', sa.Integer, sa.ForeignKey('dependants.id'), nullable=True),
        sa.Column('traveler_name', sa.String(255), nullable=False),
        sa.Column('traveler_email', sa.String(255), nullable=True),
        sa.Column('traveler_phone', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Integer, default=0, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('travel_request_travelers')
    op.drop_table('dependants')
    op.drop_table('travel_request_documents')
    op.drop_table('travel_request_messages')
    op.drop_table('travel_request_destinations')
    op.drop_table('travel_requests')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS travelertype')
    op.execute('DROP TYPE IF EXISTS dependantrelationship')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS messagesendertype')
    op.execute('DROP TYPE IF EXISTS transportmode')
    op.execute('DROP TYPE IF EXISTS travelrequeststatus')
