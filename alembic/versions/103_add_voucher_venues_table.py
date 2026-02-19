"""Add voucher_venues table for meal voucher venue associations

Revision ID: 103_add_voucher_venues
Revises: 102_add_vetting_member_submissions
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '103_add_voucher_venues'
down_revision = '102_add_vetting_member_submissions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create voucher_venues table
    op.create_table(
        'voucher_venues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('allocation_id', sa.Integer(), nullable=False),
        sa.Column('vendor_accommodation_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_accommodation_id'], ['vendor_accommodations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('allocation_id', 'vendor_accommodation_id', name='uq_allocation_venue')
    )
    op.create_index(op.f('ix_voucher_venues_id'), 'voucher_venues', ['id'], unique=False)
    op.create_index(op.f('ix_voucher_venues_allocation_id'), 'voucher_venues', ['allocation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_voucher_venues_allocation_id'), table_name='voucher_venues')
    op.drop_index(op.f('ix_voucher_venues_id'), table_name='voucher_venues')
    op.drop_table('voucher_venues')
