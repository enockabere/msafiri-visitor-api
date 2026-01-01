"""Restore primary role and add secondary vetting role

Revision ID: 019_restore_primary_role
Revises: 018_fix_vetting_role_case
Create Date: 2024-12-30 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '019_restore_primary_role'
down_revision = '018_fix_vetting_role_case'
branch_labels = None
depends_on = None

def upgrade():
    # Restore the user's primary role to SUPER_ADMIN (assuming user_id = 1 based on the logs)
    op.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE id = 1")
    
    # Add VETTING_APPROVER as a secondary role in user_roles table
    current_time = datetime.now().isoformat()
    op.execute(f"""
        INSERT INTO user_roles (user_id, role, granted_by, is_active, granted_at, created_at, updated_at)
        SELECT 1, 'VETTING_APPROVER', 'system_migration', true, '{current_time}', '{current_time}', '{current_time}'
        WHERE NOT EXISTS (
            SELECT 1 FROM user_roles WHERE user_id = 1 AND role = 'VETTING_APPROVER'
        )
    """)

def downgrade():
    # Remove the secondary vetting role
    op.execute("DELETE FROM user_roles WHERE user_id = 1 AND role = 'VETTING_APPROVER'")
    
    # Revert to VETTING_APPROVER as primary role (though this shouldn't be needed)
    op.execute("UPDATE users SET role = 'VETTING_APPROVER' WHERE id = 1")