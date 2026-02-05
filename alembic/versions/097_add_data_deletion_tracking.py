"""Add data deletion tracking fields

Revision ID: 097_add_data_deletion_tracking
Revises: 096_add_vetting_committee_approvers
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '097_add_data_deletion_tracking'
down_revision = '096_add_vetting_committee_approvers'
branch_labels = None
depends_on = None

def upgrade():
    # Add data deletion tracking fields
    op.add_column('event_participants', sa.Column('data_deleted_at', sa.DateTime(), nullable=True))
    op.add_column('event_participants', sa.Column('data_deletion_reason', sa.String(100), nullable=True))
    op.add_column('event_participants', sa.Column('original_email_hash', sa.String(64), nullable=True))

def downgrade():
    # Remove data deletion tracking fields
    op.drop_column('event_participants', 'original_email_hash')
    op.drop_column('event_participants', 'data_deletion_reason')
    op.drop_column('event_participants', 'data_deleted_at')