"""add budget fields to travel requests

Revision ID: 104_add_budget_to_travel_requests
Revises: 103_add_travel_request_approvals
Create Date: 2025-02-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '104_add_budget_to_travel_requests'
down_revision = '103_add_travel_request_approvals'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('travel_requests', sa.Column('budget_code', sa.String(100), nullable=True))
    op.add_column('travel_requests', sa.Column('activity_code', sa.String(100), nullable=True))
    op.add_column('travel_requests', sa.Column('cost_center', sa.String(100), nullable=True))
    op.add_column('travel_requests', sa.Column('section', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('travel_requests', 'section')
    op.drop_column('travel_requests', 'cost_center')
    op.drop_column('travel_requests', 'activity_code')
    op.drop_column('travel_requests', 'budget_code')
