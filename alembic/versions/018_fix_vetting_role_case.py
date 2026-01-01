"""Fix vetting role case consistency

Revision ID: 018_fix_vetting_role_case
Revises: 017_event_scanner_constraint
Create Date: 2024-12-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '018_fix_vetting_role_case'
down_revision = '017_event_scanner_constraint'
branch_labels = None
depends_on = None

def upgrade():
    # Add the missing enum values to both PostgreSQL enums
    # We need to do this outside of a transaction
    connection = op.get_bind()
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'"))
    connection.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'"))
    connection.execute(sa.text("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER'"))
    connection.execute(sa.text("ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE'"))
    connection.execute(sa.text("BEGIN"))
    
    # Delete problematic records from user_roles table using user_id
    op.execute("DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE role::text = 'vetting_approver')")
    op.execute("DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE role::text = 'vetting_committee')")
    
    # Now update the roles in users table
    op.execute("UPDATE users SET role = 'VETTING_APPROVER' WHERE role::text = 'vetting_approver'")
    op.execute("UPDATE users SET role = 'VETTING_COMMITTEE' WHERE role::text = 'vetting_committee'")

def downgrade():
    # Remove the enum values
    pass  # Cannot easily remove enum values in PostgreSQL