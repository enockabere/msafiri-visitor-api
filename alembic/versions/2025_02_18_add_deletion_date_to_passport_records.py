"""add deletion_date to passport_records

Revision ID: 2025_02_18_deletion_date
Revises: 2025_02_18_add_passport_data_fields
Create Date: 2025-02-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_18_deletion_date'
down_revision = '2025_02_18_add_passport_data_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add deletion_date column to passport_records table
    op.add_column('passport_records', sa.Column('deletion_date', sa.DateTime(), nullable=True))


def downgrade():
    # Remove deletion_date column from passport_records table
    op.drop_column('passport_records', 'deletion_date')
