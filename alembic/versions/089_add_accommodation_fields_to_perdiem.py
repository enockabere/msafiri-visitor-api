"""Add accommodation fields to per diem requests

Revision ID: 089_add_accommodation_fields
Revises: 088_add_accommodation_type
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '089_add_accommodation_fields'
down_revision = '088_add_accommodation_type'
branch_labels = None
depends_on = None


def upgrade():
    # Add accommodation_type and accommodation_name to perdiem_requests
    op.add_column('perdiem_requests', sa.Column('accommodation_type', sa.String(50), nullable=True))
    op.add_column('perdiem_requests', sa.Column('accommodation_name', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('perdiem_requests', 'accommodation_name')
    op.drop_column('perdiem_requests', 'accommodation_type')
