"""Add vetting member comments table for comment history

Revision ID: 098_add_vetting_member_comments
Revises: 097_add_vetting_member_selections
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '098_add_vetting_member_comments'
down_revision = '097_add_vetting_member_selections'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vetting_member_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('author_email', sa.String(255), nullable=False),
        sa.Column('author_name', sa.String(255), nullable=False),
        sa.Column('author_role', sa.String(50), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vetting_member_comments_event_id', 'vetting_member_comments', ['event_id'])
    op.create_index('ix_vetting_member_comments_participant_id', 'vetting_member_comments', ['participant_id'])
    op.create_index('ix_vetting_member_comments_author_email', 'vetting_member_comments', ['author_email'])


def downgrade():
    op.drop_index('ix_vetting_member_comments_author_email', 'vetting_member_comments')
    op.drop_index('ix_vetting_member_comments_participant_id', 'vetting_member_comments')
    op.drop_index('ix_vetting_member_comments_event_id', 'vetting_member_comments')
    op.drop_table('vetting_member_comments')
