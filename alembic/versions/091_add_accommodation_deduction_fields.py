"""Add accommodation deduction fields to perdiem_requests

Revision ID: 091_add_accommodation_deduction
Revises: 090_add_accommodation_rates
Create Date: 2026-02-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '091_add_accommodation_deduction'
down_revision = '090_add_accommodation_rates'
branch_labels = None
depends_on = None

def upgrade():
    # Add accommodation deduction breakdown columns to perdiem_requests table
    op.add_column('perdiem_requests', sa.Column('accommodation_days', sa.Integer(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('accommodation_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('perdiem_requests', sa.Column('accommodation_deduction', sa.Numeric(10, 2), nullable=True))
    op.add_column('perdiem_requests', sa.Column('per_diem_base_amount', sa.Numeric(10, 2), nullable=True))

def downgrade():
    op.drop_column('perdiem_requests', 'per_diem_base_amount')
    op.drop_column('perdiem_requests', 'accommodation_deduction')
    op.drop_column('perdiem_requests', 'accommodation_rate')
    op.drop_column('perdiem_requests', 'accommodation_days')
