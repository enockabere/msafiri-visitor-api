"""add_vetting_roles_to_enum

Revision ID: 78d0c1c5934b
Revises: merge_heads_fix
Create Date: 2025-12-15 03:13:37.470650

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78d0c1c5934b'
down_revision = 'merge_heads_fix'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to roletype
    op.execute("ALTER TYPE roletype ADD VALUE 'VETTING_APPROVER'")
    op.execute("ALTER TYPE roletype ADD VALUE 'VETTING_COMMITTEE'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This would require recreating the enum type
    pass