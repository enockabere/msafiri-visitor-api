"""remove_security_category_from_news_enum

Revision ID: 61b460aa1b53
Revises: 6f795ad196a7
Create Date: 2025-10-28 14:22:25.501593

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '61b460aa1b53'
down_revision = '6f795ad196a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum type without 'security'
    op.execute("ALTER TYPE newscategory RENAME TO newscategory_old")
    op.execute("CREATE TYPE newscategory AS ENUM ('health_program', 'security_briefing', 'events', 'reports', 'general', 'announcement')")
    op.execute("ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::text::newscategory")
    op.execute("DROP TYPE newscategory_old")


def downgrade() -> None:
    # Recreate old enum type with 'security'
    op.execute("ALTER TYPE newscategory RENAME TO newscategory_old")
    op.execute("CREATE TYPE newscategory AS ENUM ('health_program', 'security', 'security_briefing', 'events', 'reports', 'general', 'announcement')")
    op.execute("ALTER TABLE news_updates ALTER COLUMN category TYPE newscategory USING category::text::newscategory")
    op.execute("DROP TYPE newscategory_old")