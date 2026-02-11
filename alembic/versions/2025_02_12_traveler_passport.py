"""Add passport fields to travel_request_travelers

Revision ID: 2025_02_12_traveler_passport
Revises: fc254ac51b65
Create Date: 2025-02-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_12_traveler_passport'
down_revision = 'fc254ac51b65'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add passport fields to travel_request_travelers table
    op.add_column('travel_request_travelers',
        sa.Column('passport_file_url', sa.String(1024), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_uploaded_at', sa.DateTime(), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_number', sa.String(50), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_full_name', sa.String(255), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_date_of_birth', sa.Date(), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_expiry_date', sa.Date(), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_nationality', sa.String(100), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_gender', sa.String(20), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('passport_verified', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('travel_request_travelers',
        sa.Column('is_child_under_18', sa.Integer(), nullable=False, server_default='0'))

    # Add relation_type column to store the dependant's relationship type
    op.add_column('travel_request_travelers',
        sa.Column('relation_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('travel_request_travelers', 'relation_type')
    op.drop_column('travel_request_travelers', 'is_child_under_18')
    op.drop_column('travel_request_travelers', 'passport_verified')
    op.drop_column('travel_request_travelers', 'passport_gender')
    op.drop_column('travel_request_travelers', 'passport_nationality')
    op.drop_column('travel_request_travelers', 'passport_expiry_date')
    op.drop_column('travel_request_travelers', 'passport_date_of_birth')
    op.drop_column('travel_request_travelers', 'passport_full_name')
    op.drop_column('travel_request_travelers', 'passport_number')
    op.drop_column('travel_request_travelers', 'passport_uploaded_at')
    op.drop_column('travel_request_travelers', 'passport_file_url')
