"""Add approval data fields to perdiem_requests

Revision ID: 051_add_perdiem_approval_fields
Revises: 050_add_per_diem_approver_role
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '051_add_perdiem_approval_fields'
down_revision = '050_add_per_diem_approver_role'
branch_labels = None
depends_on = None

def upgrade():
    # Add approval data fields to perdiem_requests table
    op.add_column('perdiem_requests', sa.Column('approver_role', sa.String(100), nullable=True))
    op.add_column('perdiem_requests', sa.Column('approver_full_name', sa.String(255), nullable=True))
    op.add_column('perdiem_requests', sa.Column('budget_code', sa.String(100), nullable=True))
    op.add_column('perdiem_requests', sa.Column('activity_code', sa.String(100), nullable=True))
    op.add_column('perdiem_requests', sa.Column('cost_center', sa.String(100), nullable=True))
    op.add_column('perdiem_requests', sa.Column('section', sa.String(50), nullable=True))

def downgrade():
    # Remove approval data fields from perdiem_requests table
    op.drop_column('perdiem_requests', 'section')
    op.drop_column('perdiem_requests', 'cost_center')
    op.drop_column('perdiem_requests', 'activity_code')
    op.drop_column('perdiem_requests', 'budget_code')
    op.drop_column('perdiem_requests', 'approver_full_name')
    op.drop_column('perdiem_requests', 'approver_role')