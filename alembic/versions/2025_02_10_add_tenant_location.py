"""add city and coordinates to tenants

Revision ID: add_tenant_location
Revises: 
Create Date: 2025-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_10_add_tenant_location'
down_revision = 'add_currency_rates'
branch_labels = None
depends_on = None


def upgrade():
    # Add city and coordinates columns to tenants table
    op.add_column('tenants', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('tenants', sa.Column('latitude', sa.String(20), nullable=True))
    op.add_column('tenants', sa.Column('longitude', sa.String(20), nullable=True))


def downgrade():
    # Remove city and coordinates columns from tenants table
    op.drop_column('tenants', 'longitude')
    op.drop_column('tenants', 'latitude')
    op.drop_column('tenants', 'city')
