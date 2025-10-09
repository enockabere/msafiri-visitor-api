"""Add direct_messages table

Revision ID: 002_add_direct_messages
Revises: b5a42d5c4bd7
Create Date: 2024-10-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_direct_messages'
down_revision = 'b5a42d5c4bd7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create direct_messages table
    op.create_table('direct_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_email', sa.String(length=255), nullable=False),
        sa.Column('sender_name', sa.String(length=255), nullable=True),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_direct_messages_sender', 'direct_messages', ['sender_email'])
    op.create_index('idx_direct_messages_recipient', 'direct_messages', ['recipient_email'])
    op.create_index('idx_direct_messages_tenant', 'direct_messages', ['tenant_id'])

def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_direct_messages_tenant', table_name='direct_messages')
    op.drop_index('idx_direct_messages_recipient', table_name='direct_messages')
    op.drop_index('idx_direct_messages_sender', table_name='direct_messages')
    
    # Drop table
    op.drop_table('direct_messages')