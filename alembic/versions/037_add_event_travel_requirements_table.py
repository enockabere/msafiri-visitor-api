"""add_event_travel_requirements_table

Revision ID: 037_add_event_travel_requirements_table
Revises: 036_fix_form_responses_foreign_key
Create Date: 2024-01-19 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '037_add_event_travel_requirements_table'
down_revision = '036_fix_form_responses_foreign_key'
branch_labels = None
depends_on = None


def upgrade():
    # Create event_travel_requirements table using String for requirement_type
    op.create_table('event_travel_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('requirement_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), nullable=True),
        sa.Column('deadline_days_before', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_travel_requirements_id'), 'event_travel_requirements', ['id'], unique=False)
    
    # Create participant_requirement_status table
    op.create_table('participant_requirement_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('requirement_id', sa.Integer(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('completed_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ),
        sa.ForeignKeyConstraint(['requirement_id'], ['event_travel_requirements.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participant_requirement_status_id'), 'participant_requirement_status', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_participant_requirement_status_id'), table_name='participant_requirement_status')
    op.drop_table('participant_requirement_status')
    op.drop_index(op.f('ix_event_travel_requirements_id'), table_name='event_travel_requirements')
    op.drop_table('event_travel_requirements')