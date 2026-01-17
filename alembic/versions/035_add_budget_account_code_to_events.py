"""add budget account code to events

Revision ID: 035_add_budget_account_code
Revises: 034_fix_notification_priority_type
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '035_add_budget_account_code'
down_revision = '034_fix_notification_priority_type'
branch_labels = None
depends_on = None

def upgrade():
    # Add budget_account_code column to events table
    op.add_column('events', sa.Column('budget_account_code', sa.String(10), nullable=True))

def downgrade():
    # Remove budget_account_code column from events table
    op.drop_column('events', 'budget_account_code')