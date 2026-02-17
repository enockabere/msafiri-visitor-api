"""add rates to guest houses

Revision ID: 109_add_rates_to_guest_houses
Revises: 108_add_perdiem_approval_steps
Create Date: 2025-02-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '109_add_rates_to_guest_houses'
down_revision = '108_add_perdiem_approval_steps'
branch_labels = None
depends_on = None


def upgrade():
    # Add rate columns to guest_houses table
    op.add_column('guest_houses', sa.Column('fullboard_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('guest_houses', sa.Column('halfboard_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('guest_houses', sa.Column('bed_and_breakfast_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('guest_houses', sa.Column('bed_only_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('guest_houses', sa.Column('currency', sa.String(3), nullable=True, server_default='KES'))


def downgrade():
    # Remove rate columns from guest_houses table
    op.drop_column('guest_houses', 'currency')
    op.drop_column('guest_houses', 'bed_only_rate')
    op.drop_column('guest_houses', 'bed_and_breakfast_rate')
    op.drop_column('guest_houses', 'halfboard_rate')
    op.drop_column('guest_houses', 'fullboard_rate')
