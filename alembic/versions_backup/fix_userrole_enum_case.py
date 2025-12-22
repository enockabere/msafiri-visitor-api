"""Fix UserRole enum case consistency

Revision ID: fix_userrole_enum_case
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'fix_userrole_enum_case'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Update existing enum values to match the model
    op.execute("UPDATE users SET role = 'super_admin' WHERE role = 'SUPER_ADMIN'")
    op.execute("UPDATE users SET role = 'mt_admin' WHERE role = 'MT_ADMIN'")
    op.execute("UPDATE users SET role = 'hr_admin' WHERE role = 'HR_ADMIN'")
    op.execute("UPDATE users SET role = 'event_admin' WHERE role = 'EVENT_ADMIN'")
    op.execute("UPDATE users SET role = 'visitor' WHERE role = 'VISITOR'")
    op.execute("UPDATE users SET role = 'guest' WHERE role = 'GUEST'")
    op.execute("UPDATE users SET role = 'staff' WHERE role = 'STAFF'")

def downgrade():
    # Revert to uppercase
    op.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE role = 'super_admin'")
    op.execute("UPDATE users SET role = 'MT_ADMIN' WHERE role = 'mt_admin'")
    op.execute("UPDATE users SET role = 'HR_ADMIN' WHERE role = 'hr_admin'")
    op.execute("UPDATE users SET role = 'EVENT_ADMIN' WHERE role = 'event_admin'")
    op.execute("UPDATE users SET role = 'VISITOR' WHERE role = 'visitor'")
    op.execute("UPDATE users SET role = 'GUEST' WHERE role = 'guest'")
    op.execute("UPDATE users SET role = 'STAFF' WHERE role = 'staff'")