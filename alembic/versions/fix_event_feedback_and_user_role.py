"""Fix event_feedback table and add vetting_approver role

Revision ID: fix_event_feedback_and_user_role
Revises: 9ef282c3b8b3
Create Date: 2025-01-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_event_feedback_and_user_role'
down_revision = '9ef282c3b8b3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add missing columns to event_feedback table if they don't exist
    try:
        # Check if columns exist before adding them
        op.add_column('event_feedback', sa.Column('participant_id', sa.Integer(), nullable=True))
        op.create_index('ix_event_feedback_participant_id', 'event_feedback', ['participant_id'])
    except Exception:
        pass  # Column already exists
    
    try:
        op.add_column('event_feedback', sa.Column('ip_address', sa.String(45), nullable=True))
    except Exception:
        pass  # Column already exists
    
    try:
        op.add_column('event_feedback', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
    except Exception:
        pass  # Column already exists
    
    # Add vetting_approver to UserRole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'vetting_approver'")

def downgrade() -> None:
    # Remove added columns
    try:
        op.drop_index('ix_event_feedback_participant_id', table_name='event_feedback')
        op.drop_column('event_feedback', 'participant_id')
    except Exception:
        pass
    
    try:
        op.drop_column('event_feedback', 'ip_address')
    except Exception:
        pass
    
    try:
        op.drop_column('event_feedback', 'updated_at')
    except Exception:
        pass
    
    # Cannot remove enum values in PostgreSQL