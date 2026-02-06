"""Add vetting chat tables for committee discussions

Revision ID: 099_add_vetting_chat_tables
Revises: 098_add_vetting_member_comments
Create Date: 2025-02-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '099_add_vetting_chat_tables'
down_revision = '098_add_vetting_member_comments'
branch_labels = None
depends_on = None


def upgrade():
    # Update ChatType enum to include VETTING_CHAT
    # Note: PostgreSQL requires special handling for enum updates
    # For SQLite and other databases, this may work differently

    # Create vetting_chat_rooms table
    op.create_table(
        'vetting_chat_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_room_id', sa.Integer(), nullable=False),
        sa.Column('vetting_committee_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), default=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_reason', sa.String(100), nullable=True),
        sa.Column('event_end_date', sa.Date(), nullable=True),
        sa.Column('scheduled_deletion_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['chat_room_id'], ['chat_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vetting_committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_room_id')
    )
    op.create_index('ix_vetting_chat_rooms_event_id', 'vetting_chat_rooms', ['event_id'])
    op.create_index('ix_vetting_chat_rooms_vetting_committee_id', 'vetting_chat_rooms', ['vetting_committee_id'])

    # Create vetting_chat_members table
    op.create_table(
        'vetting_chat_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vetting_chat_id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('user_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('can_send_messages', sa.Boolean(), default=True),
        sa.Column('muted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('muted_reason', sa.String(100), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['vetting_chat_id'], ['vetting_chat_rooms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vetting_chat_members_user_email', 'vetting_chat_members', ['user_email'])
    op.create_index('ix_vetting_chat_members_vetting_chat_id', 'vetting_chat_members', ['vetting_chat_id'])


def downgrade():
    op.drop_index('ix_vetting_chat_members_vetting_chat_id', 'vetting_chat_members')
    op.drop_index('ix_vetting_chat_members_user_email', 'vetting_chat_members')
    op.drop_table('vetting_chat_members')

    op.drop_index('ix_vetting_chat_rooms_vetting_committee_id', 'vetting_chat_rooms')
    op.drop_index('ix_vetting_chat_rooms_event_id', 'vetting_chat_rooms')
    op.drop_table('vetting_chat_rooms')
