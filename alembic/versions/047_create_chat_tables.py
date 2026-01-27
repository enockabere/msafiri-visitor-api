"""create_chat_tables

Revision ID: 047_create_chat_tables
Revises: 046
Create Date: 2025-01-27 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '047_create_chat_tables'
down_revision = '046'  # Update this to your latest migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create chattype enum
    chattype_enum = postgresql.ENUM('direct_message', 'event_chatroom', name='chattype')
    chattype_enum.create(op.get_bind())
    
    # Create chat_rooms table
    op.create_table('chat_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_type', chattype_enum, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
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
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('reply_to_message_id', sa.Integer(), nullable=True),
        sa.Column('is_admin_message', sa.Boolean(), nullable=True),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
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
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('reply_to_message_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['reply_to_message_id'], ['direct_messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_direct_messages_id'), 'direct_messages', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_direct_messages_id'), table_name='direct_messages')
    op.drop_table('direct_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_rooms_id'), table_name='chat_rooms')
    op.drop_table('chat_rooms')
    
    # Drop chattype enum
    chattype_enum = postgresql.ENUM('direct_message', 'event_chatroom', name='chattype')
    chattype_enum.drop(op.get_bind())