"""merge multiple heads

Revision ID: 069_merge_heads
Revises: 065fff04a21e, 068_add_modified_by
Create Date: 2024-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '069_merge_heads'
down_revision = ('065fff04a21e', '068_add_modified_by')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no changes needed
    pass


def downgrade():
    # This is a merge migration - no changes needed
    pass