"""Update perdiem status enum values

Revision ID: update_perdiem_status_enum
Revises: 
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_perdiem_status_enum'
down_revision = None
depends_on = None


def upgrade():
    # First, update existing data to new values
    op.execute("UPDATE perdiem_requests SET status = 'open' WHERE status = 'pending' AND admin_notes = 'CANCELLED_BY_USER'")
    op.execute("UPDATE perdiem_requests SET status = 'pending_approval' WHERE status = 'pending'")
    op.execute("UPDATE perdiem_requests SET status = 'approved' WHERE status = 'line_manager_approved'")
    op.execute("UPDATE perdiem_requests SET status = 'approved' WHERE status = 'budget_owner_approved'")
    op.execute("UPDATE perdiem_requests SET status = 'completed' WHERE status = 'paid'")
    
    # Drop the old enum type and create new one
    op.execute("ALTER TYPE perdiemstatus RENAME TO perdiemstatus_old")
    op.execute("CREATE TYPE perdiemstatus AS ENUM ('open', 'pending_approval', 'approved', 'rejected', 'issued', 'completed')")
    op.execute("ALTER TABLE perdiem_requests ALTER COLUMN status TYPE perdiemstatus USING status::text::perdiemstatus")
    op.execute("DROP TYPE perdiemstatus_old")


def downgrade():
    # Revert to old enum values
    op.execute("UPDATE perdiem_requests SET status = 'pending' WHERE status = 'pending_approval'")
    op.execute("UPDATE perdiem_requests SET status = 'line_manager_approved' WHERE status = 'approved'")
    op.execute("UPDATE perdiem_requests SET status = 'paid' WHERE status = 'completed'")
    
    # Recreate old enum
    op.execute("ALTER TYPE perdiemstatus RENAME TO perdiemstatus_old")
    op.execute("CREATE TYPE perdiemstatus AS ENUM ('pending', 'line_manager_approved', 'budget_owner_approved', 'rejected', 'paid')")
    op.execute("ALTER TABLE perdiem_requests ALTER COLUMN status TYPE perdiemstatus USING status::text::perdiemstatus")
    op.execute("DROP TYPE perdiemstatus_old")