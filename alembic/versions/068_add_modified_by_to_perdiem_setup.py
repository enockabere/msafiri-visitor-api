"""add_modified_by_to_perdiem_setup

Revision ID: 068_add_modified_by
Revises: 067_create_perdiem_setup
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '068_add_modified_by'
down_revision = '067_create_perdiem_setup'
branch_labels = None
depends_on = None


def upgrade():
    # Add modified_by column to perdiem_setup table
    op.add_column('perdiem_setup', sa.Column('modified_by', sa.String(255), nullable=True))


def downgrade():
    # Remove modified_by column from perdiem_setup table
    op.drop_column('perdiem_setup', 'modified_by')