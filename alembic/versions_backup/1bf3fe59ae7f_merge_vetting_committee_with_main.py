"""merge vetting committee with main

Revision ID: 1bf3fe59ae7f
Revises: 779de758951b, add_vetting_committee
Create Date: 2025-12-12 17:00:03.728797

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bf3fe59ae7f'
down_revision = ('779de758951b', 'add_vetting_committee')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass