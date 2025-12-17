"""merge_enum_fix

Revision ID: 9ef282c3b8b3
Revises: pub_reg_table, fix_userrole_enum_case
Create Date: 2025-12-14 20:55:02.044520

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ef282c3b8b3'
down_revision = ('pub_reg_table', 'fix_userrole_enum_case')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass