"""add travelling_from_country to public_registrations

Revision ID: f1a2b3c4d5e6
Revises: a8587dd42ea8
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'a8587dd42ea8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add travelling_from_country column to public_registrations table"""
    op.add_column('public_registrations', 
                  sa.Column('travelling_from_country', sa.String(100), nullable=True))


def downgrade() -> None:
    """Remove travelling_from_country column from public_registrations table"""
    op.drop_column('public_registrations', 'travelling_from_country')