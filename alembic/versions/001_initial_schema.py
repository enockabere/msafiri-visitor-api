"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This migration represents the current state of the database
    # All tables already exist, so we just mark this as the baseline
    pass

def downgrade() -> None:
    # Cannot downgrade from initial schema
    pass