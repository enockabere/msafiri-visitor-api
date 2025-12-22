"""add_attachment_fields_to_chat_messages

Revision ID: 085532e32bfb
Revises: 002_consolidate_participant_data
Create Date: 2025-12-22 11:27:47.569551

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '085532e32bfb'
down_revision = '002_consolidate_participant_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add attachment fields to chat_messages table
    op.add_column('chat_messages', sa.Column('file_url', sa.String(length=500), nullable=True))
    op.add_column('chat_messages', sa.Column('file_type', sa.String(length=50), nullable=True))
    op.add_column('chat_messages', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('chat_messages', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('chat_messages', sa.Column('duration', sa.Integer(), nullable=True))

    # Make message column nullable in chat_messages
    op.alter_column('chat_messages', 'message', nullable=True)

    # Add attachment fields to direct_messages table
    op.add_column('direct_messages', sa.Column('file_url', sa.String(length=500), nullable=True))
    op.add_column('direct_messages', sa.Column('file_type', sa.String(length=50), nullable=True))
    op.add_column('direct_messages', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('direct_messages', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('direct_messages', sa.Column('duration', sa.Integer(), nullable=True))

    # Make message column nullable in direct_messages
    op.alter_column('direct_messages', 'message', nullable=True)


def downgrade() -> None:
    # Remove attachment fields from chat_messages table
    op.drop_column('chat_messages', 'duration')
    op.drop_column('chat_messages', 'file_size')
    op.drop_column('chat_messages', 'file_name')
    op.drop_column('chat_messages', 'file_type')
    op.drop_column('chat_messages', 'file_url')

    # Make message column not nullable again in chat_messages
    op.alter_column('chat_messages', 'message', nullable=False)

    # Remove attachment fields from direct_messages table
    op.drop_column('direct_messages', 'duration')
    op.drop_column('direct_messages', 'file_size')
    op.drop_column('direct_messages', 'file_name')
    op.drop_column('direct_messages', 'file_type')
    op.drop_column('direct_messages', 'file_url')

    # Make message column not nullable again in direct_messages
    op.alter_column('direct_messages', 'message', nullable=False)