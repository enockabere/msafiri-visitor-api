"""Add contact fields to badge templates

Revision ID: 010_add_contact_fields_to_badge_templates
Revises: 009_badge_templates
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_contact_fields'
down_revision = '009_badge_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Add contact_phone and website_url columns to badge_templates table
    op.add_column('badge_templates', sa.Column('contact_phone', sa.String(length=50), nullable=True))
    op.add_column('badge_templates', sa.Column('website_url', sa.String(length=255), nullable=True))


def downgrade():
    # Remove contact_phone and website_url columns from badge_templates table
    op.drop_column('badge_templates', 'website_url')
    op.drop_column('badge_templates', 'contact_phone')