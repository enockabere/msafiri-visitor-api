"""fix duplicate migration heads

Revision ID: 070_fix_duplicate_heads
Revises: 069_merge_heads
Create Date: 2024-12-19 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '070_fix_duplicate_heads'
down_revision = '069_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure currency column exists in perdiem_requests
    try:
        op.add_column('perdiem_requests', sa.Column('currency', sa.String(10), server_default='USD'))
    except Exception:
        # Column already exists, skip
        pass


def downgrade():
    # Remove currency column if needed
    try:
        op.drop_column('perdiem_requests', 'currency')
    except Exception:
        # Column doesn't exist, skip
        pass