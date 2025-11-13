"""Create event_voucher_scanners table for event-specific scanner tracking

Revision ID: create_event_voucher_scanners
Revises: 
Create Date: 2024-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_event_voucher_scanners'
down_revision = None  # Update this to the latest revision ID
branch_labels = None
depends_on = None


def upgrade():
    """Create event_voucher_scanners table for event-specific scanner tracking"""
    
    # Create the event_voucher_scanners table
    op.create_table('event_voucher_scanners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_user_event_scanner')
    )
    
    # Create indexes for better performance
    op.create_index('idx_event_voucher_scanners_event_id', 'event_voucher_scanners', ['event_id'])
    op.create_index('idx_event_voucher_scanners_user_id', 'event_voucher_scanners', ['user_id'])
    op.create_index('idx_event_voucher_scanners_tenant_id', 'event_voucher_scanners', ['tenant_id'])
    op.create_index('idx_event_voucher_scanners_active', 'event_voucher_scanners', ['is_active'])


def downgrade():
    """Drop event_voucher_scanners table and indexes"""
    
    # Drop indexes first
    op.drop_index('idx_event_voucher_scanners_active', table_name='event_voucher_scanners')
    op.drop_index('idx_event_voucher_scanners_tenant_id', table_name='event_voucher_scanners')
    op.drop_index('idx_event_voucher_scanners_user_id', table_name='event_voucher_scanners')
    op.drop_index('idx_event_voucher_scanners_event_id', table_name='event_voucher_scanners')
    
    # Drop the table
    op.drop_table('event_voucher_scanners')