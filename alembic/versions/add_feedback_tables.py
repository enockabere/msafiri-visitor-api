"""Add feedback tables

Revision ID: add_feedback_tables
Revises: 
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_feedback_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create agenda_feedback table
    op.create_table('agenda_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agenda_id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(), nullable=False),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agenda_id'], ['event_agenda.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agenda_feedback_id'), 'agenda_feedback', ['id'], unique=False)

    # Create feedback_responses table
    op.create_table('feedback_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_id', sa.Integer(), nullable=False),
        sa.Column('responder_email', sa.String(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('is_like', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['feedback_id'], ['agenda_feedback.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_responses_id'), 'feedback_responses', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_feedback_responses_id'), table_name='feedback_responses')
    op.drop_table('feedback_responses')
    op.drop_index(op.f('ix_agenda_feedback_id'), table_name='agenda_feedback')
    op.drop_table('agenda_feedback')