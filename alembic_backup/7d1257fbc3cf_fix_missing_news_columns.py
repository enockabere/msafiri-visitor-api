"""fix_missing_news_columns

Revision ID: 7d1257fbc3cf
Revises: add_external_link_news
Create Date: 2025-10-28 11:06:15.644422

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d1257fbc3cf'
down_revision = 'add_external_link_news'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to news_updates table
    op.add_column('news_updates', sa.Column('external_link', sa.String(500), nullable=True))
    op.add_column('news_updates', sa.Column('content_type', sa.String(20), nullable=True, default='text'))
    op.add_column('news_updates', sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('news_updates', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove the columns
    op.drop_column('news_updates', 'expires_at')
    op.drop_column('news_updates', 'scheduled_publish_at')
    op.drop_column('news_updates', 'content_type')
    op.drop_column('news_updates', 'external_link')