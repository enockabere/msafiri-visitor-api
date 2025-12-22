"""create_participant_voucher_redemptions_table

Revision ID: 75292896db1f
Revises: 005_event_certificates
Create Date: 2025-12-22 14:35:40.750043

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75292896db1f'
down_revision = '005_event_certificates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create participant_voucher_redemptions table
    op.create_table('participant_voucher_redemptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('allocation_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('redeemed_at', sa.DateTime(), nullable=False),
        sa.Column('redeemed_by', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['allocation_id'], ['event_allocations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_participant_voucher_redemptions_allocation_id', 'participant_voucher_redemptions', ['allocation_id'])
    op.create_index('ix_participant_voucher_redemptions_participant_id', 'participant_voucher_redemptions', ['participant_id'])


def downgrade() -> None:
    op.drop_index('ix_participant_voucher_redemptions_participant_id', table_name='participant_voucher_redemptions')
    op.drop_index('ix_participant_voucher_redemptions_allocation_id', table_name='participant_voucher_redemptions')
    op.drop_table('participant_voucher_redemptions')