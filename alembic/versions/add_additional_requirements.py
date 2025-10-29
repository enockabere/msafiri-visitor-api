"""Add additional_requirements to country_travel_requirements

Revision ID: add_additional_requirements
Revises: 148b242d4e59
Create Date: 2024-10-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_additional_requirements'
down_revision = '148b242d4e59'
branch_labels = None
depends_on = None


def upgrade():
    # Add additional_requirements column to country_travel_requirements table
    op.add_column('country_travel_requirements', 
                  sa.Column('additional_requirements', postgresql.JSON(), nullable=True))


def downgrade():
    # Remove additional_requirements column
    op.drop_column('country_travel_requirements', 'additional_requirements')