"""remove currency default from perdiem_requests

Revision ID: 091
Revises: 090
Create Date: 2026-02-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '091'
down_revision = '090'
branch_labels = None
depends_on = None


def upgrade():
    # Remove server default from currency column
    op.alter_column('perdiem_requests', 'currency',
                    existing_type=sa.String(10),
                    server_default=None,
                    nullable=False)


def downgrade():
    # Add back server default
    op.alter_column('perdiem_requests', 'currency',
                    existing_type=sa.String(10),
                    server_default='USD',
                    nullable=False)
