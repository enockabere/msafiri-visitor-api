"""Create chat tables

Revision ID: create_chat_tables
Revises: create_invitations_table
Create Date: 2024-10-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_chat_tables'
down_revision = 'create_invitations_table'
depends_on = None


def upgrade():
    # Create chat_rooms table
    op.create_table('chat_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_type', sa.Enum('DIRECT_MESSAGE', 'EVENT_CHATROOM', name='chattype'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_rooms_id'), 'chat_rooms', ['id'], unique=False)

    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_room_id', sa.Integer(), nullable=False),
        sa.Column('sender_email', sa.String(length=255), nullable=False),
        sa.Column('sender_name', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('reply_to_message_id', sa.Integer(), nullable=True),
        sa.Column('is_admin_message', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['chat_room_id'], ['chat_rooms.id'], ),
        sa.ForeignKeyConstraint(['reply_to_message_id'], ['chat_messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

    # Create direct_messages table
    op.create_table('direct_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_email', sa.String(length=255), nullable=False),
        sa.Column('sender_name', sa.String(length=255), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('recipient_name', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_direct_messages_id'), 'direct_messages', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_direct_messages_id'), table_name='direct_messages')
    op.drop_table('direct_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_rooms_id'), table_name='chat_rooms')
    op.drop_table('chat_rooms')
    op.execute('DROP TYPE IF EXISTS chattype')