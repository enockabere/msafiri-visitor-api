"""merge_multiple_heads

Revision ID: a24c6988176d
Revises: 007_add_vetting_approver_role, 086fix_dm_seq, 75292896db1f
Create Date: 2025-12-23 16:33:50.803262

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a24c6988176d'
down_revision = ('007_add_vetting_approver_role', '086fix_dm_seq', '75292896db1f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass