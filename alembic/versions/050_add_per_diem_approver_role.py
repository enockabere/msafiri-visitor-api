"""add_per_diem_approver_role

Revision ID: 050_add_per_diem_approver_role
Revises: 049_update_perdiem_approver_fields
Create Date: 2025-01-27 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '050_add_per_diem_approver_role'
down_revision = '049_update_perdiem_approver_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add PER_DIEM_APPROVER to the roletype enum
    op.execute("ALTER TYPE roletype ADD VALUE 'PER_DIEM_APPROVER'")

def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass