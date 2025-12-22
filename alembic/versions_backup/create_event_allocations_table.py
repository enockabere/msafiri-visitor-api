"""create_event_allocations_table

Revision ID: create_event_allocations_table
Revises: create_inventory_table
Create Date: 2025-12-14 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_event_allocations_table'
down_revision = 'create_inventory_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create event_allocations table
    op.create_table('event_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('inventory_item_id', sa.Integer(), nullable=True),
        sa.Column('quantity_per_participant', sa.Integer(), nullable=True),
        sa.Column('drink_vouchers_per_participant', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('approved_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_allocations_id'), 'event_allocations', ['id'], unique=False)

    # Create event_voucher_scanners table
    op.create_table('event_voucher_scanners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_voucher_scanners_id'), 'event_voucher_scanners', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_event_voucher_scanners_id'), table_name='event_voucher_scanners')
    op.drop_table('event_voucher_scanners')
    op.drop_index(op.f('ix_event_allocations_id'), table_name='event_allocations')
    op.drop_table('event_allocations')