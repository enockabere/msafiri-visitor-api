"""add currency to claims

Revision ID: 067_add_currency
Revises: 066_add_currency_column
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '067_add_currency'
down_revision = '066_add_currency_column'
branch_labels = None
depends_on = None


def upgrade():
    # Add currency column to claims table
    op.add_column('claims', sa.Column('currency', sa.String(length=3), nullable=True))
    op.execute("UPDATE claims SET currency = 'KES' WHERE currency IS NULL")
    
    # Add currency column to claim_items table
    op.add_column('claim_items', sa.Column('currency', sa.String(length=3), nullable=True))
    op.execute("UPDATE claim_items SET currency = 'KES' WHERE currency IS NULL")


def downgrade():
    op.drop_column('claim_items', 'currency')
    op.drop_column('claims', 'currency')
