"""Merge heads fix

Revision ID: merge_heads_fix
Revises: add_missing_enum_values, fix_event_feedback_and_user_role
Create Date: 2025-01-02 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_fix'
down_revision = ('add_missing_enum_values', 'fix_event_feedback_and_user_role')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass