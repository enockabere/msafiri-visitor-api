"""Remove accommodation rate columns from perdiem_setup table

Revision ID: 2025_02_17_remove_accom_rates
Revises: 2025_02_16_advance_payment
Create Date: 2025-02-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_17_remove_accom_rates'
down_revision = '2025_02_16_advance_payment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop accommodation rate columns from perdiem_setup table
    op.drop_column('perdiem_setup', 'fullboard_rate')
    op.drop_column('perdiem_setup', 'halfboard_rate')
    op.drop_column('perdiem_setup', 'bed_and_breakfast_rate')
    op.drop_column('perdiem_setup', 'bed_only_rate')


def downgrade() -> None:
    # Re-add accommodation rate columns if needed
    op.add_column('perdiem_setup',
        sa.Column('fullboard_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup',
        sa.Column('halfboard_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup',
        sa.Column('bed_and_breakfast_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
    op.add_column('perdiem_setup',
        sa.Column('bed_only_rate', sa.Numeric(10, 2), nullable=True, server_default='0'))
