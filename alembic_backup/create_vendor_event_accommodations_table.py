"""Create vendor_event_accommodations table

Revision ID: vendor_event_accommodations
Revises: 53d5f6cdf36b
Create Date: 2025-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'vendor_event_accommodations'
down_revision = '53d5f6cdf36b'
branch_labels = None
depends_on = None


def upgrade():
    # Create vendor_event_accommodations table
    op.create_table('vendor_event_accommodations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('vendor_accommodation_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('event_name', sa.String(length=200), nullable=True),
        sa.Column('single_rooms', sa.Integer(), nullable=False, default=0),
        sa.Column('double_rooms', sa.Integer(), nullable=False, default=0),
        sa.Column('total_capacity', sa.Integer(), nullable=False),
        sa.Column('current_occupants', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_vendor_event_accommodations_id', 'vendor_event_accommodations', ['id'])
    op.create_index('ix_vendor_event_accommodations_tenant_id', 'vendor_event_accommodations', ['tenant_id'])
    op.create_index('ix_vendor_event_accommodations_vendor_id', 'vendor_event_accommodations', ['vendor_accommodation_id'])
    op.create_index('ix_vendor_event_accommodations_event_id', 'vendor_event_accommodations', ['event_id'])
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_vendor_event_accommodations_vendor_accommodation_id',
        'vendor_event_accommodations', 'vendor_accommodations',
        ['vendor_accommodation_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_vendor_event_accommodations_event_id',
        'vendor_event_accommodations', 'events',
        ['event_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_vendor_event_accommodations_event_id', 'vendor_event_accommodations', type_='foreignkey')
    op.drop_constraint('fk_vendor_event_accommodations_vendor_accommodation_id', 'vendor_event_accommodations', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_vendor_event_accommodations_event_id', 'vendor_event_accommodations')
    op.drop_index('ix_vendor_event_accommodations_vendor_id', 'vendor_event_accommodations')
    op.drop_index('ix_vendor_event_accommodations_tenant_id', 'vendor_event_accommodations')
    op.drop_index('ix_vendor_event_accommodations_id', 'vendor_event_accommodations')
    
    # Drop table
    op.drop_table('vendor_event_accommodations')