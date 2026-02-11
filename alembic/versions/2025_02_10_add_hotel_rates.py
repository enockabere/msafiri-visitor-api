"""add hotel rates to vendor accommodations

Revision ID: add_hotel_rates
Revises: 
Create Date: 2025-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_hotel_rates'
down_revision = None  # Update this with your latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Add rate columns to vendor_accommodations table
    op.add_column('vendor_accommodations', sa.Column('rate_bed_breakfast', sa.Numeric(10, 2), nullable=True))
    op.add_column('vendor_accommodations', sa.Column('rate_half_board', sa.Numeric(10, 2), nullable=True))
    op.add_column('vendor_accommodations', sa.Column('rate_full_board', sa.Numeric(10, 2), nullable=True))
    op.add_column('vendor_accommodations', sa.Column('rate_bed_only', sa.Numeric(10, 2), nullable=True))


def downgrade():
    # Remove rate columns from vendor_accommodations table
    op.drop_column('vendor_accommodations', 'rate_bed_only')
    op.drop_column('vendor_accommodations', 'rate_full_board')
    op.drop_column('vendor_accommodations', 'rate_half_board')
    op.drop_column('vendor_accommodations', 'rate_bed_breakfast')
