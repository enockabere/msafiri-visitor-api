"""Add CHAT_MENTION to notification type enum

Revision ID: add_chat_mention_enum
Revises: add_updated_at_passport
Create Date: 2024-11-04 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_chat_mention_enum'
down_revision = 'add_updated_at_passport'
branch_labels = None
depends_on = None


def upgrade():
    # Add CHAT_MENTION to the notification type enum
    op.execute("ALTER TYPE notificationtype ADD VALUE 'CHAT_MENTION'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass