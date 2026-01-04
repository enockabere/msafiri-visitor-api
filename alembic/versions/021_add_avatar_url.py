"""add avatar_url to users

Revision ID: 021_add_avatar_url
Revises: 3a0cfc969d7b
Create Date: 2025-01-04 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_add_avatar_url'
down_revision = '3a0cfc969d7b'
branch_labels = None
depends_on = None


def upgrade():
    # Add avatar_url column to users table
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade():
    # Remove avatar_url column from users table
    op.drop_column('users', 'avatar_url')