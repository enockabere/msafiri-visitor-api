"""add_line_manager_recommendations_table

Revision ID: 006_add_line_manager_recommendations
Revises: 005_event_certificates
Create Date: 2025-01-02 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_line_mgr_rec'
down_revision = '005_event_certificates'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'line_manager_recommendations' not in inspector.get_table_names():
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
            sa.Column('contact_type', sa.String(), nullable=True),  # Added for HRCO, Career Manager, Line Manager
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        )
        
        # Create indexes
        op.create_index('ix_line_manager_recommendations_participant_email', 'line_manager_recommendations', ['participant_email'])
        op.create_index('ix_line_manager_recommendations_event_id', 'line_manager_recommendations', ['event_id'])
        op.create_index('ix_line_manager_recommendations_token', 'line_manager_recommendations', ['recommendation_token'])

def downgrade() -> None:
    op.drop_table('line_manager_recommendations')