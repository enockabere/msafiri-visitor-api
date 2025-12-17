"""Add APP_FEEDBACK to notification type enum

Revision ID: simple_add_app_feedback
Revises: 61b460aa1b53
Create Date: 2025-10-28 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'simple_add_app_feedback'
down_revision = '61b460aa1b53'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add APP_FEEDBACK to the notification type enum
    op.execute("ALTER TYPE notificationtype ADD VALUE 'APP_FEEDBACK'")

def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type
    pass