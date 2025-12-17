"""Remove accommodation_type from vendor_accommodations

Revision ID: remove_accommodation_type
Revises: 
Create Date: 2025-12-04 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_accommodation_type'
down_revision = None  # Will be set when generated
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove accommodation_type column from vendor_accommodations table
    op.drop_column('vendor_accommodations', 'accommodation_type')


def downgrade() -> None:
    # Add accommodation_type column back
    op.add_column('vendor_accommodations', 
                  sa.Column('accommodation_type', sa.String(100), nullable=False, server_default='hotel'))