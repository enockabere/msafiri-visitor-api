"""add currency field to perdiem_requests fixed

Revision ID: 065fff04a21e
Revises: 35176d8605de
Create Date: 2024-12-19 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '065fff04a21e'
down_revision = '35176d8605de'
branch_labels = None
depends_on = None


def upgrade():
    # Add currency column to perdiem_requests if it doesn't exist
    try:
        op.add_column('perdiem_requests', sa.Column('currency', sa.String(10), server_default='USD'))
    except Exception:
        # Column might already exist, skip
        pass


def downgrade():
    # Remove currency column
    try:
        op.drop_column('perdiem_requests', 'currency')
    except Exception:
        # Column might not exist, skip
        pass