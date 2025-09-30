"""Add reply_to_message_id to chat_messages

Revision ID: add_reply_to_message_id
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_reply_to_message_id'
down_revision = 'add_must_change_password'
depends_on = None


def upgrade():
    # Add reply_to_message_id column to chat_messages table
    op.add_column('chat_messages', sa.Column('reply_to_message_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_chat_messages_reply_to_message_id',
        'chat_messages', 
        'chat_messages',
        ['reply_to_message_id'], 
        ['id']
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_chat_messages_reply_to_message_id', 'chat_messages', type_='foreignkey')
    
    # Drop column
    op.drop_column('chat_messages', 'reply_to_message_id')