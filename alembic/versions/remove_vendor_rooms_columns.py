"""Remove single_rooms and double_rooms from vendor_accommodations

Revision ID: remove_vendor_rooms_columns
Revises: 53d5f6cdf36b
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_vendor_rooms_columns'
down_revision = '53d5f6cdf36b'
branch_labels = None
depends_on = None


def upgrade():
    # Remove single_rooms and double_rooms columns from vendor_accommodations table
    op.drop_column('vendor_accommodations', 'single_rooms')
    op.drop_column('vendor_accommodations', 'double_rooms')


def downgrade():
    # Add back single_rooms and double_rooms columns
    op.add_column('vendor_accommodations', sa.Column('single_rooms', sa.Integer(), nullable=True, default=0))
    op.add_column('vendor_accommodations', sa.Column('double_rooms', sa.Integer(), nullable=True, default=0))