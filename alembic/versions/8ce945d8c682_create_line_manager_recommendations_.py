"""create_line_manager_recommendations_table

Revision ID: 8ce945d8c682
Revises: 980a0d680dc8
Create Date: 2025-12-17 10:41:44.995705

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ce945d8c682'
down_revision = '980a0d680dc8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create line_manager_recommendations table
    op.create_table(
        'line_manager_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('participant_name', sa.String(), nullable=False),
        sa.Column('participant_email', sa.String(), nullable=False),
        sa.Column('line_manager_email', sa.String(), nullable=False),
        sa.Column('operation_center', sa.String(), nullable=True),
        sa.Column('event_title', sa.String(), nullable=True),
        sa.Column('event_dates', sa.String(), nullable=True),
        sa.Column('event_location', sa.String(), nullable=True),
        sa.Column('is_recommended', sa.Boolean(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('recommendation_token', sa.String(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.Index('ix_line_manager_recommendations_participant_email', 'participant_email'),
        sa.Index('ix_line_manager_recommendations_event_id', 'event_id'),
        sa.Index('ix_line_manager_recommendations_token', 'recommendation_token')
    )


def downgrade() -> None:
    op.drop_table('line_manager_recommendations')