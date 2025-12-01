"""Fix chat messages cascade delete

Revision ID: fix_chat_messages_cascade_delete
Revises: create_transport_requests
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'fix_chat_messages_cascade_delete'
down_revision = 'create_transport_requests'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing foreign key constraints if they exist
    try:
        op.drop_constraint('chat_messages_chat_room_id_fkey', 'chat_messages', type_='foreignkey')
    except:
        pass  # Constraint might not exist or have a different name
    
    try:
        op.drop_constraint('chat_messages_reply_to_message_id_fkey', 'chat_messages', type_='foreignkey')
    except:
        pass  # Constraint might not exist or have a different name
    
    # Add foreign key constraint with CASCADE DELETE for chat_room_id
    op.create_foreign_key(
        'chat_messages_chat_room_id_fkey',
        'chat_messages', 
        'chat_rooms',
        ['chat_room_id'], 
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add foreign key constraint with SET NULL for reply_to_message_id (self-referential)
    op.create_foreign_key(
        'chat_messages_reply_to_message_id_fkey',
        'chat_messages', 
        'chat_messages',
        ['reply_to_message_id'], 
        ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    # Drop the cascade constraints
    op.drop_constraint('chat_messages_chat_room_id_fkey', 'chat_messages', type_='foreignkey')
    op.drop_constraint('chat_messages_reply_to_message_id_fkey', 'chat_messages', type_='foreignkey')
    
    # Recreate without cascade
    op.create_foreign_key(
        'chat_messages_chat_room_id_fkey',
        'chat_messages', 
        'chat_rooms',
        ['chat_room_id'], 
        ['id']
    )
    
    op.create_foreign_key(
        'chat_messages_reply_to_message_id_fkey',
        'chat_messages', 
        'chat_messages',
        ['reply_to_message_id'], 
        ['id']
    )