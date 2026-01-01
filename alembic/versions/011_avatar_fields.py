"""Add avatar fields to badge templates

Revision ID: 011_avatar_fields
Revises: 010_contact_fields
Create Date: 2024-01-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_avatar_fields'
down_revision = '010_contact_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add avatar_url and include_avatar columns to badge_templates table
    op.add_column('badge_templates', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('badge_templates', sa.Column('include_avatar', sa.Boolean(), nullable=True, default=False))


def downgrade():
    # Remove avatar_url and include_avatar columns from badge_templates table
    op.drop_column('badge_templates', 'include_avatar')
    op.drop_column('badge_templates', 'avatar_url')