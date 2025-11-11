"""Add VOUCHER_SCANNER role type

Revision ID: add_voucher_scanner_role
Revises: voucher_redemption_001
Create Date: 2024-11-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_voucher_scanner_role'
down_revision = 'voucher_redemption_001'
depends_on = None

def upgrade():
    # Add VOUCHER_SCANNER to the roletype enum
    op.execute("ALTER TYPE roletype ADD VALUE 'VOUCHER_SCANNER'")

def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type
    pass