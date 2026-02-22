"""add bank transfer payment method

Revision ID: 2026_02_22_bank_transfer
Revises: 2026_02_21_add_event_and_visa_fields
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_02_22_bank_transfer'
down_revision = '2026_02_21_event_visa'
branch_labels = None
depends_on = None


def upgrade():
    # Add BANK_TRANSFER to paymentmethod enum
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'BANK_TRANSFER'")
    
    # Add bank_account_id column (nullable, no foreign key since bank_accounts table may not exist)
    op.add_column('perdiem_requests', sa.Column('bank_account_id', sa.Integer(), nullable=True))


def downgrade():
    # Remove column
    op.drop_column('perdiem_requests', 'bank_account_id')
    
    # Note: Cannot remove enum value in PostgreSQL without recreating the enum
