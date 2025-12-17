"""merge_heads

Revision ID: 6f795ad196a7
Revises: 7d1257fbc3cf, add_video_document_urls
Create Date: 2025-10-28 14:22:18.975440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f795ad196a7'
down_revision = ('7d1257fbc3cf', 'add_video_document_urls')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass