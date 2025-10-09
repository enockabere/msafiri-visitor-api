"""Base migration

Revision ID: 001_base
Revises: b5a42d5c4bd7
Create Date: 2024-10-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_base'
down_revision = 'b5a42d5c4bd7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This is a base migration - no changes needed
    pass

def downgrade() -> None:
    # This is a base migration - no changes needed
    pass