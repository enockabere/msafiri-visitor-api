"""Update vetting committee status enum

Revision ID: update_vetting_status_enum
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_vetting_status_enum'
down_revision = None
depends_on = None

def upgrade():
    # Create new enum type
    new_vetting_status = postgresql.ENUM('open', 'pending_approval', 'approved', name='vettingstatus_new')
    new_vetting_status.create(op.get_bind())
    
    # Update existing records to map old values to new values
    op.execute("""
        UPDATE vetting_committees 
        SET status = CASE 
            WHEN status = 'pending' THEN 'open'
            WHEN status = 'in_progress' THEN 'open'
            WHEN status = 'submitted_for_approval' THEN 'pending_approval'
            WHEN status = 'completed' THEN 'approved'
            ELSE 'open'
        END::text
    """)
    
    # Alter column to use new enum
    op.execute("ALTER TABLE vetting_committees ALTER COLUMN status TYPE vettingstatus_new USING status::text::vettingstatus_new")
    
    # Drop old enum
    op.execute("DROP TYPE IF EXISTS vettingstatus")
    
    # Rename new enum to original name
    op.execute("ALTER TYPE vettingstatus_new RENAME TO vettingstatus")

def downgrade():
    # Create old enum type
    old_vetting_status = postgresql.ENUM('pending', 'in_progress', 'completed', 'submitted_for_approval', name='vettingstatus_old')
    old_vetting_status.create(op.get_bind())
    
    # Update records back to old values
    op.execute("""
        UPDATE vetting_committees 
        SET status = CASE 
            WHEN status = 'open' THEN 'pending'
            WHEN status = 'pending_approval' THEN 'submitted_for_approval'
            WHEN status = 'approved' THEN 'completed'
            ELSE 'pending'
        END::text
    """)
    
    # Alter column to use old enum
    op.execute("ALTER TABLE vetting_committees ALTER COLUMN status TYPE vettingstatus_old USING status::text::vettingstatus_old")
    
    # Drop new enum
    op.execute("DROP TYPE IF EXISTS vettingstatus")
    
    # Rename old enum to original name
    op.execute("ALTER TYPE vettingstatus_old RENAME TO vettingstatus")