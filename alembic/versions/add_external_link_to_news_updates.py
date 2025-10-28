"""add external link to news updates

Revision ID: add_external_link_news
Revises: 7ecda31119dc
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_external_link_news'
down_revision = '7ecda31119dc'
branch_labels = None
depends_on = None

def upgrade():
    # Add external_link column
    op.add_column('news_updates', sa.Column('external_link', sa.String(500), nullable=True))
    
    # Add content_type column with default value
    op.add_column('news_updates', sa.Column('content_type', sa.String(20), nullable=False, server_default='text'))
    
    # Add scheduled_publish_at column
    op.add_column('news_updates', sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    # Remove the columns
    op.drop_column('news_updates', 'external_link')
    op.drop_column('news_updates', 'content_type')
    op.drop_column('news_updates', 'scheduled_publish_at')