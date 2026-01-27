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
    # Create the new enum type first
    op.execute("CREATE TYPE perdiemstatus AS ENUM ('open', 'pending_approval', 'approved', 'rejected', 'issued', 'completed')")
    
    # Add a temporary column with the new enum type
    op.add_column('perdiem_requests', sa.Column('status_new', sa.Enum('open', 'pending_approval', 'approved', 'rejected', 'issued', 'completed', name='perdiemstatus'), nullable=True))
    
    # Update the new column based on existing status values
    op.execute("UPDATE perdiem_requests SET status_new = 'open' WHERE status = 'pending' AND admin_notes = 'CANCELLED_BY_USER'")
    op.execute("UPDATE perdiem_requests SET status_new = 'pending_approval' WHERE status = 'pending' AND (admin_notes IS NULL OR admin_notes != 'CANCELLED_BY_USER')")
    op.execute("UPDATE perdiem_requests SET status_new = 'approved' WHERE status = 'line_manager_approved'")
    op.execute("UPDATE perdiem_requests SET status_new = 'approved' WHERE status = 'budget_owner_approved'")
    op.execute("UPDATE perdiem_requests SET status_new = 'rejected' WHERE status = 'rejected'")
    op.execute("UPDATE perdiem_requests SET status_new = 'completed' WHERE status = 'paid'")
    
    # Set default for any remaining NULL values
    op.execute("UPDATE perdiem_requests SET status_new = 'open' WHERE status_new IS NULL")
    
    # Drop the old status column
    op.drop_column('perdiem_requests', 'status')
    
    # Rename the new column to status
    op.execute("ALTER TABLE perdiem_requests RENAME COLUMN status_new TO status")
    
    # Make the column NOT NULL
    op.execute("ALTER TABLE perdiem_requests ALTER COLUMN status SET NOT NULL")


def downgrade():
    # Add temporary column with old enum values
    op.execute("CREATE TYPE perdiemstatus_old AS ENUM ('pending', 'line_manager_approved', 'budget_owner_approved', 'rejected', 'paid')")
    op.add_column('perdiem_requests', sa.Column('status_old', sa.Enum('pending', 'line_manager_approved', 'budget_owner_approved', 'rejected', 'paid', name='perdiemstatus_old'), nullable=True))
    
    # Convert back to old values
    op.execute("UPDATE perdiem_requests SET status_old = 'pending' WHERE status = 'pending_approval'")
    op.execute("UPDATE perdiem_requests SET status_old = 'line_manager_approved' WHERE status = 'approved'")
    op.execute("UPDATE perdiem_requests SET status_old = 'paid' WHERE status = 'completed'")
    op.execute("UPDATE perdiem_requests SET status_old = 'rejected' WHERE status = 'rejected'")
    op.execute("UPDATE perdiem_requests SET status_old = 'pending' WHERE status = 'open'")
    op.execute("UPDATE perdiem_requests SET status_old = 'pending' WHERE status = 'issued'")
    
    # Drop new column and rename old
    op.drop_column('perdiem_requests', 'status')
    op.execute("ALTER TABLE perdiem_requests RENAME COLUMN status_old TO status")
    op.execute("ALTER TABLE perdiem_requests ALTER COLUMN status SET NOT NULL")
    
    # Drop new enum and rename old
    op.execute("DROP TYPE perdiemstatus")
    op.execute("ALTER TYPE perdiemstatus_old RENAME TO perdiemstatus")