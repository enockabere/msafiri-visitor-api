"""merge heads

Revision ID: fc254ac51b65
Revises: 2025_02_10_add_tenant_location, 80ae7bedc9bf
Create Date: 2026-02-11 10:33:07.831006

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc254ac51b65'
down_revision = ('2025_02_10_add_tenant_location', '80ae7bedc9bf')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
