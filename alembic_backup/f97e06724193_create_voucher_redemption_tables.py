"""create_voucher_redemption_tables

Revision ID: f97e06724193
Revises: d1a2b3c4d5e6
Create Date: 2025-12-10 13:01:41.830431

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f97e06724193'
down_revision = 'd1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create participant_voucher_redemptions table
    op.create_table('participant_voucher_redemptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('allocation_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('redeemed_at', sa.DateTime(), nullable=False),
        sa.Column('redeemed_by', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participant_voucher_redemptions_id'), 'participant_voucher_redemptions', ['id'], unique=False)
    op.create_index('idx_participant_voucher_redemptions_allocation', 'participant_voucher_redemptions', ['allocation_id'], unique=False)
    op.create_index('idx_participant_voucher_redemptions_participant', 'participant_voucher_redemptions', ['participant_id'], unique=False)

    # Create pending_voucher_redemptions table
    op.create_table('pending_voucher_redemptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('allocation_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_voucher_redemptions_id'), 'pending_voucher_redemptions', ['id'], unique=False)
    op.create_index(op.f('ix_pending_voucher_redemptions_token'), 'pending_voucher_redemptions', ['token'], unique=True)
    op.create_index('idx_pending_voucher_redemptions_allocation', 'pending_voucher_redemptions', ['allocation_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_pending_voucher_redemptions_allocation', table_name='pending_voucher_redemptions')
    op.drop_index(op.f('ix_pending_voucher_redemptions_token'), table_name='pending_voucher_redemptions')
    op.drop_index(op.f('ix_pending_voucher_redemptions_id'), table_name='pending_voucher_redemptions')
    op.drop_table('pending_voucher_redemptions')
    
    op.drop_index('idx_participant_voucher_redemptions_participant', table_name='participant_voucher_redemptions')
    op.drop_index('idx_participant_voucher_redemptions_allocation', table_name='participant_voucher_redemptions')
    op.drop_index(op.f('ix_participant_voucher_redemptions_id'), table_name='participant_voucher_redemptions')
    op.drop_table('participant_voucher_redemptions')