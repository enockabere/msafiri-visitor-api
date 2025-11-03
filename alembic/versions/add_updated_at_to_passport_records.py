"""Add updated_at column to passport_records table

Revision ID: add_updated_at_passport
Revises: passport_records_001
Create Date: 2024-11-03 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_updated_at_passport'
down_revision = 'passport_records_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column if it doesn't exist
    op.add_column('passport_records', 
                  sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove updated_at column
    op.drop_column('passport_records', 'updated_at')