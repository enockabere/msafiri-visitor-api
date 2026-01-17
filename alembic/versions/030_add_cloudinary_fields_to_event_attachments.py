"""Add Cloudinary fields to event_attachments

Revision ID: 030_add_cloudinary_fields
Revises: 029_add_contact_type
Create Date: 2026-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030_add_cloudinary_fields'
down_revision = '029_add_contact_type'
branch_labels = None
depends_on = None

def upgrade():
    # Add Cloudinary metadata columns to event_attachments table
    op.add_column('event_attachments', sa.Column('public_id', sa.String(255), nullable=True))
    op.add_column('event_attachments', sa.Column('file_type', sa.String(100), nullable=True))
    op.add_column('event_attachments', sa.Column('resource_type', sa.String(50), nullable=True))
    op.add_column('event_attachments', sa.Column('original_filename', sa.String(255), nullable=True))

def downgrade():
    # Remove Cloudinary metadata columns
    op.drop_column('event_attachments', 'original_filename')
    op.drop_column('event_attachments', 'resource_type')
    op.drop_column('event_attachments', 'file_type')
    op.drop_column('event_attachments', 'public_id')