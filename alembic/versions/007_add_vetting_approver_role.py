"""Add VETTING_APPROVER role to UserRole enum

Revision ID: 007_add_vetting_approver_role
Revises: 006_add_line_manager_recommendations
Create Date: 2024-12-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_vetting_approver_role'
down_revision = '006_line_mgr_rec'
branch_labels = None
depends_on = None

def upgrade():
    # Add vetting_approver to the UserRole enum (lowercase with underscore)
    op.execute("ALTER TYPE userrole ADD VALUE 'vetting_approver'")

def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass