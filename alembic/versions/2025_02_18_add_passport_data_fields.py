"""Add passport data fields to passport_records table

Revision ID: 2025_02_18_passport_data
Revises:
Create Date: 2025-02-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_02_18_passport_data'
down_revision = None  # Will be set by Alembic
branch_labels = None
depends_on = None


def upgrade():
    # Add passport data columns to passport_records table
    # These columns store passport data extracted by Document Intelligence
    # instead of relying on external API

    # Check if columns exist before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('passport_records')]

    if 'passport_number' not in columns:
        op.add_column('passport_records', sa.Column('passport_number', sa.String(50), nullable=True))

    if 'given_names' not in columns:
        op.add_column('passport_records', sa.Column('given_names', sa.String(255), nullable=True))

    if 'surname' not in columns:
        op.add_column('passport_records', sa.Column('surname', sa.String(255), nullable=True))

    if 'date_of_birth' not in columns:
        op.add_column('passport_records', sa.Column('date_of_birth', sa.String(20), nullable=True))

    if 'date_of_expiry' not in columns:
        op.add_column('passport_records', sa.Column('date_of_expiry', sa.String(20), nullable=True))

    if 'date_of_issue' not in columns:
        op.add_column('passport_records', sa.Column('date_of_issue', sa.String(20), nullable=True))

    if 'gender' not in columns:
        op.add_column('passport_records', sa.Column('gender', sa.String(10), nullable=True))

    if 'nationality' not in columns:
        op.add_column('passport_records', sa.Column('nationality', sa.String(100), nullable=True))

    if 'issue_country' not in columns:
        op.add_column('passport_records', sa.Column('issue_country', sa.String(100), nullable=True))

    if 'passport_image_url' not in columns:
        op.add_column('passport_records', sa.Column('passport_image_url', sa.Text(), nullable=True))


def downgrade():
    # Remove the passport data columns
    op.drop_column('passport_records', 'passport_image_url')
    op.drop_column('passport_records', 'issue_country')
    op.drop_column('passport_records', 'nationality')
    op.drop_column('passport_records', 'gender')
    op.drop_column('passport_records', 'date_of_issue')
    op.drop_column('passport_records', 'date_of_expiry')
    op.drop_column('passport_records', 'date_of_birth')
    op.drop_column('passport_records', 'surname')
    op.drop_column('passport_records', 'given_names')
    op.drop_column('passport_records', 'passport_number')
