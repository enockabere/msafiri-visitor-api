"""create chat_rooms table

Revision ID: create_chat_rooms
Revises: 
Create Date: 2025-01-15 09:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_chat_rooms'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create chat_rooms table
    op.create_table('chat_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add foreign key constraints
    op.create_foreign_key(None, 'chat_rooms', 'events', ['event_id'], ['id'])
    op.create_foreign_key(None, 'chat_rooms', 'tenants', ['tenant_id'], ['id'])
    op.create_foreign_key(None, 'chat_rooms', 'users', ['created_by'], ['id'])
    
    # Add indexes
    op.create_index('ix_chat_rooms_tenant_id', 'chat_rooms', ['tenant_id'])
    op.create_index('ix_chat_rooms_event_id', 'chat_rooms', ['event_id'])
    op.create_index('ix_chat_rooms_is_active', 'chat_rooms', ['is_active'])

def downgrade():
    op.drop_table('chat_rooms')