"""add_country_column_to_tenants

Revision ID: add_country_column
Revises: b5a42d5c4bd7
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_country_column'
down_revision = 'b5a42d5c4bd7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add country column to tenants table
    op.add_column('tenants', sa.Column('country', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove country column from tenants table
    op.drop_column('tenants', 'country')