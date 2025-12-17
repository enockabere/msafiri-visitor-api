"""Add video_url, document_url fields and security_briefing category

Revision ID: add_video_document_urls
Revises: add_external_link_news
Create Date: 2025-10-28 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_video_document_urls'
down_revision = 'add_external_link_news'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('news_updates', sa.Column('video_url', sa.String(500), nullable=True))
    op.add_column('news_updates', sa.Column('document_url', sa.String(500), nullable=True))
    
    # Update enum to include security_briefing
    op.execute("ALTER TYPE newscategory ADD VALUE 'security_briefing'")

def downgrade():
    # Remove columns
    op.drop_column('news_updates', 'document_url')
    op.drop_column('news_updates', 'video_url')
    
    # Note: Cannot remove enum values in PostgreSQL easily