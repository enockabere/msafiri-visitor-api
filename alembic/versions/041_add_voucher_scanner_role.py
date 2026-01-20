"""Add VOUCHER_SCANNER role type

Revision ID: 041_add_voucher_scanner_role
Revises: 040_add_user_roles_table
Create Date: 2025-01-20 22:52:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '041_add_voucher_scanner_role'
down_revision = '040_add_user_roles_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add VOUCHER_SCANNER to the roletype enum
    op.execute("ALTER TYPE roletype ADD VALUE 'VOUCHER_SCANNER'")

def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type
    pass