"""Merge migration heads

Revision ID: 004_merge_heads
Revises: 003_add_participant_qr_table, comprehensive_fixes
Create Date: 2025-01-27 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_merge_heads'
down_revision = ('003_add_participant_qr_table', 'comprehensive_fixes')
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This is a merge migration - no changes needed
    pass

def downgrade() -> None:
    # This is a merge migration - no changes needed
    pass