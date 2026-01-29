"""add currency column

Revision ID: 066_add_currency_column
Revises: 35176d8605de
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '066_add_currency_column'
down_revision = '35176d8605de'
branch_labels = None
depends_on = None

def upgrade():
    # Add currency column to perdiem_requests
    op.add_column('perdiem_requests', sa.Column('currency', sa.String(10), server_default='USD'))

def downgrade():
    # Remove currency column
    op.drop_column('perdiem_requests', 'currency')