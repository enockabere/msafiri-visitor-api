"""Create voucher redemption tables

Revision ID: voucher_redemption_001
Revises: 
Create Date: 2024-11-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'voucher_redemption_001'
down_revision = None
depends_on = None

def upgrade():
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
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_voucher_redemptions_id'), 'pending_voucher_redemptions', ['id'], unique=False)
    op.create_index(op.f('ix_pending_voucher_redemptions_token'), 'pending_voucher_redemptions', ['token'], unique=True)

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
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participant_voucher_redemptions_id'), 'participant_voucher_redemptions', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_participant_voucher_redemptions_id'), table_name='participant_voucher_redemptions')
    op.drop_table('participant_voucher_redemptions')
    op.drop_index(op.f('ix_pending_voucher_redemptions_token'), table_name='pending_voucher_redemptions')
    op.drop_index(op.f('ix_pending_voucher_redemptions_id'), table_name='pending_voucher_redemptions')
    op.drop_table('pending_voucher_redemptions')