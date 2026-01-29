"""Fix usertenantrole enum values

Revision ID: a503b7c001fc
Revises: 070_fix_duplicate_heads
Create Date: 2026-01-29 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a503b7c001fc'
down_revision = '070_fix_duplicate_heads'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing FINANCE_ADMIN value to the enum
    op.execute("ALTER TYPE usertenantrole ADD VALUE 'FINANCE_ADMIN'")

def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass