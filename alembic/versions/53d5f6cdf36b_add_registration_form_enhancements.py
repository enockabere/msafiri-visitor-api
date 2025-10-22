"""Add registration form enhancements

Revision ID: 53d5f6cdf36b
Revises: 79e2f043a024
Create Date: 2025-10-22 11:28:51.294191

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '53d5f6cdf36b'
down_revision = '79e2f043a024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new fields to public_registrations table
    op.add_column('public_registrations', sa.Column('badge_name', sa.String(255), nullable=True))
    op.add_column('public_registrations', sa.Column('motivation_letter', sa.Text(), nullable=True))
    op.add_column('public_registrations', sa.Column('email_checked', sa.Boolean(), default=False, nullable=True))
    op.add_column('public_registrations', sa.Column('recommendation_requested', sa.Boolean(), default=False, nullable=True))
    
    # Create line_manager_recommendations table
    op.create_table('line_manager_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('participant_name', sa.String(255), nullable=False),
        sa.Column('participant_email', sa.String(255), nullable=False),
        sa.Column('line_manager_email', sa.String(255), nullable=False),
        sa.Column('operation_center', sa.String(50), nullable=True),
        sa.Column('event_title', sa.String(255), nullable=True),
        sa.Column('event_dates', sa.String(100), nullable=True),
        sa.Column('event_location', sa.String(255), nullable=True),
        sa.Column('recommendation_token', sa.String(255), nullable=False),
        sa.Column('recommendation_text', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['registration_id'], ['public_registrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recommendation_token')
    )
    
    # Create indexes for better performance
    op.create_index('idx_recommendations_token', 'line_manager_recommendations', ['recommendation_token'])
    op.create_index('idx_recommendations_event_id', 'line_manager_recommendations', ['event_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_recommendations_event_id', 'line_manager_recommendations')
    op.drop_index('idx_recommendations_token', 'line_manager_recommendations')
    
    # Drop line_manager_recommendations table
    op.drop_table('line_manager_recommendations')
    
    # Remove columns from public_registrations
    op.drop_column('public_registrations', 'recommendation_requested')
    op.drop_column('public_registrations', 'email_checked')
    op.drop_column('public_registrations', 'motivation_letter')
    op.drop_column('public_registrations', 'badge_name')