"""Add board_type, rate_per_day, currency to accommodation_allocations

Revision ID: 2025_02_17_board_type_rate
Revises: 2025_02_17_remove_accom_rates
Create Date: 2025-02-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_17_board_type_rate'
down_revision = '2025_02_17_remove_accom_rates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add board_type column (FullBoard, HalfBoard, BedAndBreakfast, BedOnly)
    op.add_column('accommodation_allocations',
        sa.Column('board_type', sa.String(50), nullable=True))

    # Add rate_per_day column (daily rate from vendor hotel or guesthouse)
    op.add_column('accommodation_allocations',
        sa.Column('rate_per_day', sa.Numeric(10, 2), nullable=True))

    # Add rate_currency column
    op.add_column('accommodation_allocations',
        sa.Column('rate_currency', sa.String(3), nullable=True, server_default='KES'))


def downgrade() -> None:
    op.drop_column('accommodation_allocations', 'rate_currency')
    op.drop_column('accommodation_allocations', 'rate_per_day')
    op.drop_column('accommodation_allocations', 'board_type')
