"""merge availability and other heads

Revision ID: 4a2aaf238a99
Revises: 3c95d2b9dc8b, add_availability_contacts
Create Date: 2025-10-27 10:51:26.177173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a2aaf238a99'
down_revision = ('3c95d2b9dc8b', 'add_availability_contacts')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass