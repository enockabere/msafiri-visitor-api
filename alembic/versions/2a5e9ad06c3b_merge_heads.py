"""merge_heads

Revision ID: 2a5e9ad06c3b
Revises: add_document_fields, add_vetting_comments
Create Date: 2025-12-18 09:53:20.554600

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a5e9ad06c3b'
down_revision = ('add_document_fields', 'add_vetting_comments')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass