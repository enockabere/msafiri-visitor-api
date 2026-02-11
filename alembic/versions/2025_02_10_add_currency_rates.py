"""add currency to vendor accommodations

Revision ID: add_currency_rates
Revises: add_hotel_rates
Create Date: 2025-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_currency_rates'
down_revision = 'add_hotel_rates'
branch_labels = None
depends_on = None


def upgrade():
    # Add currency column with default KES
    op.add_column('vendor_accommodations', sa.Column('rate_currency', sa.String(3), nullable=False, server_default='KES'))


def downgrade():
    # Remove currency column
    op.drop_column('vendor_accommodations', 'rate_currency')
