"""Add approval tracking columns to perdiem_requests

Revision ID: add_perdiem_approval_columns
Revises: 
Create Date: 2025-01-27 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_perdiem_approval_columns'
down_revision = None
depends_on = None


def upgrade():
    # Add approval tracking columns
    op.add_column('perdiem_requests', sa.Column('approved_by', sa.String(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('perdiem_requests', sa.Column('rejected_by', sa.String(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove approval tracking columns
    op.drop_column('perdiem_requests', 'rejected_at')
    op.drop_column('perdiem_requests', 'rejected_by')
    op.drop_column('perdiem_requests', 'approved_at')
    op.drop_column('perdiem_requests', 'approved_by')