"""create_event_feedback_table

Revision ID: create_event_feedback_table
Revises: create_event_allocations_table
Create Date: 2025-12-14 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_event_feedback_table'
down_revision = 'create_event_allocations_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create event_feedback table
    op.create_table('event_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('participant_name', sa.String(length=255), nullable=True),
        sa.Column('participant_email', sa.String(length=255), nullable=True),
        sa.Column('feedback_type', sa.String(length=50), nullable=True),
        sa.Column('overall_rating', sa.Integer(), nullable=True),
        sa.Column('content_rating', sa.Integer(), nullable=True),
        sa.Column('organization_rating', sa.Integer(), nullable=True),
        sa.Column('venue_rating', sa.Integer(), nullable=True),
        sa.Column('accommodation_rating', sa.Integer(), nullable=True),
        sa.Column('transport_rating', sa.Integer(), nullable=True),
        sa.Column('food_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('suggestions', sa.Text(), nullable=True),
        sa.Column('would_recommend', sa.Boolean(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_feedback_id'), 'event_feedback', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_event_feedback_id'), table_name='event_feedback')
    op.drop_table('event_feedback')