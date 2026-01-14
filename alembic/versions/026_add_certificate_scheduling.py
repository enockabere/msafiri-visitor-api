"""add certificate scheduling fields

Revision ID: 026_certificate_scheduling
Revises: 025
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_certificate_scheduling'
down_revision = 'add_tenant_public_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add certificate_date to event_certificates table
    op.add_column('event_certificates', sa.Column('certificate_date', sa.DateTime(), nullable=True))
    
    # Add is_published flag to control when certificates are visible
    op.add_column('event_certificates', sa.Column('is_published', sa.Boolean(), server_default='false', nullable=False))
    
    # Add email_sent flag to track if notification emails were sent
    op.add_column('participant_certificates', sa.Column('email_sent', sa.Boolean(), server_default='false', nullable=False))
    
    # Add email_sent_at timestamp
    op.add_column('participant_certificates', sa.Column('email_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('participant_certificates', 'email_sent_at')
    op.drop_column('participant_certificates', 'email_sent')
    op.drop_column('event_certificates', 'is_published')
    op.drop_column('event_certificates', 'certificate_date')
