"""Add document fields to code_of_conduct

Revision ID: add_document_fields
Revises: [previous_revision_id]
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_document_fields'
down_revision = '2a5e9ad06c3b'  # Points to the merge revision
branch_labels = None
depends_on = None

def upgrade():
    # Add document_url and document_public_id columns
    op.add_column('code_of_conduct', sa.Column('document_url', sa.String(500), nullable=True))
    op.add_column('code_of_conduct', sa.Column('document_public_id', sa.String(255), nullable=True))

def downgrade():
    # Remove the added columns
    op.drop_column('code_of_conduct', 'document_public_id')
    op.drop_column('code_of_conduct', 'document_url')