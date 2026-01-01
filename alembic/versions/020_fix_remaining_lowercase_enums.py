"""Fix remaining lowercase enum values

Revision ID: 020_fix_remaining_lowercase_enums
Revises: 019_restore_primary_role
Create Date: 2024-12-30 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '020_fix_lowercase_enums'
down_revision = '019_restore_primary_role'
branch_labels = None
depends_on = None

def upgrade():
    # Fix any remaining lowercase enum values in user_roles table
    op.execute("UPDATE user_roles SET role = 'VETTING_APPROVER' WHERE role::text = 'vetting_approver'")
    op.execute("UPDATE user_roles SET role = 'VETTING_COMMITTEE' WHERE role::text = 'vetting_committee'")
    op.execute("UPDATE user_roles SET role = 'SUPER_ADMIN' WHERE role::text = 'super_admin'")
    op.execute("UPDATE user_roles SET role = 'MT_ADMIN' WHERE role::text = 'mt_admin'")
    op.execute("UPDATE user_roles SET role = 'HR_ADMIN' WHERE role::text = 'hr_admin'")
    op.execute("UPDATE user_roles SET role = 'EVENT_ADMIN' WHERE role::text = 'event_admin'")
    
    # Fix any remaining lowercase enum values in users table
    op.execute("UPDATE users SET role = 'VETTING_APPROVER' WHERE role::text = 'vetting_approver'")
    op.execute("UPDATE users SET role = 'VETTING_COMMITTEE' WHERE role::text = 'vetting_committee'")
    op.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE role::text = 'super_admin'")
    op.execute("UPDATE users SET role = 'MT_ADMIN' WHERE role::text = 'mt_admin'")
    op.execute("UPDATE users SET role = 'HR_ADMIN' WHERE role::text = 'hr_admin'")
    op.execute("UPDATE users SET role = 'EVENT_ADMIN' WHERE role::text = 'event_admin'")

def downgrade():
    # Revert to lowercase (though this shouldn't be needed)
    pass