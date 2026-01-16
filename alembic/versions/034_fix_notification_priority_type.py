"""fix notification priority type

Revision ID: 034_fix_priority
Revises: 033_add_poa_slug
Create Date: 2025-01-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '034_fix_priority'
down_revision = '033_add_poa_slug'
branch_labels = None
depends_on = None

def upgrade():
    # Change priority column from ENUM to VARCHAR
    op.execute("ALTER TABLE notifications ALTER COLUMN priority DROP DEFAULT")
    op.execute("ALTER TABLE notifications ALTER COLUMN priority TYPE VARCHAR(20) USING priority::text")
    op.execute("ALTER TABLE notifications ALTER COLUMN priority SET DEFAULT 'MEDIUM'")
    
    # Update NULL values to MEDIUM
    op.execute("UPDATE notifications SET priority = 'MEDIUM' WHERE priority IS NULL")
    
    # Ensure all values are uppercase
    op.execute("UPDATE notifications SET priority = UPPER(priority) WHERE priority IS NOT NULL")

def downgrade():
    # Revert back to ENUM (optional, may cause issues if data doesn't match enum values)
    op.execute("ALTER TABLE notifications ALTER COLUMN priority DROP DEFAULT")
    op.execute("ALTER TABLE notifications ALTER COLUMN priority TYPE VARCHAR(20)")
    op.execute("ALTER TABLE notifications ALTER COLUMN priority SET DEFAULT 'MEDIUM'")
