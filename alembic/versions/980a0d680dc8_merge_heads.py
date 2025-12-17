"""merge_heads

Revision ID: 980a0d680dc8
Revises: add_form_fields_001, e0f959f9b399, update_vetting_status_enum
Create Date: 2025-12-17 09:54:48.028447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '980a0d680dc8'
down_revision = ('add_form_fields_001', 'e0f959f9b399', 'update_vetting_status_enum')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass