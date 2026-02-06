"""Add vetting member selections table

Revision ID: 097_add_vetting_member_selections
Revises: 096_add_vetting_committee_approvers
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '097_add_vetting_member_selections'
down_revision = '096_add_vetting_committee_approvers'
branch_labels = None
depends_on = None


def upgrade():
    # Create vetting_member_selections table
    op.create_table('vetting_member_selections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('member_email', sa.String(255), nullable=False),
        sa.Column('selection', sa.String(20), nullable=False),  # 'selected', 'not_selected'
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'participant_id', 'member_email', name='unique_member_participant_selection')
    )
    
    # Create indexes
    op.create_index('idx_vetting_member_selections_event_participant', 'vetting_member_selections', ['event_id', 'participant_id'])
    op.create_index('idx_vetting_member_selections_member', 'vetting_member_selections', ['member_email'])


def downgrade():
    op.drop_index('idx_vetting_member_selections_member', table_name='vetting_member_selections')
    op.drop_index('idx_vetting_member_selections_event_participant', table_name='vetting_member_selections')
    op.drop_table('vetting_member_selections')