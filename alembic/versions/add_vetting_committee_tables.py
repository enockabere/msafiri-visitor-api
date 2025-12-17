"""Add vetting committee tables

Revision ID: add_vetting_committee
Revises: 4c8f57e5312c
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_vetting_committee'
down_revision = '4c8f57e5312c'
branch_labels = None
depends_on = None

def upgrade():
    # Add new user roles
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'vetting_committee'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'approver'")
    
    # Create vetting_committees table
    op.create_table('vetting_committees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('selection_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('selection_end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=True, default='pending'),
        sa.Column('approver_email', sa.String(255), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_by', sa.String(255), nullable=True),
        sa.Column('approval_status', sa.String(50), nullable=True, default='pending'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vetting_committees_event_id', 'vetting_committees', ['event_id'])
    
    # Create vetting_committee_members table
    op.create_table('vetting_committee_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('invitation_sent', sa.Boolean(), default=False),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invitation_token', sa.String(255), nullable=True),
        sa.Column('first_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vetting_committee_members_committee_id', 'vetting_committee_members', ['committee_id'])
    op.create_index('idx_vetting_committee_members_email', 'vetting_committee_members', ['email'])
    
    # Create participant_selections table
    op.create_table('participant_selections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('selected', sa.Boolean(), nullable=False),
        sa.Column('selection_notes', sa.Text(), nullable=True),
        sa.Column('selected_by', sa.String(255), nullable=False),
        sa.Column('selected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approver_override', sa.Boolean(), default=False),
        sa.Column('override_notes', sa.Text(), nullable=True),
        sa.Column('override_by', sa.String(255), nullable=True),
        sa.Column('override_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('committee_id', 'participant_id')
    )
    op.create_index('idx_participant_selections_committee_id', 'participant_selections', ['committee_id'])
    op.create_index('idx_participant_selections_participant_id', 'participant_selections', ['participant_id'])

def downgrade():
    # Drop tables
    op.drop_table('participant_selections')
    op.drop_table('vetting_committee_members')
    op.drop_table('vetting_committees')
    
    # Note: Cannot remove enum values in PostgreSQL easily, so we leave them