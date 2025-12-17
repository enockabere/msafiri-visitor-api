"""Merge migration heads

Revision ID: 86bb3be9b7e0
Revises: add_decline_fields, remove_vendor_rooms_columns
Create Date: 2025-10-23 09:30:43.962359

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86bb3be9b7e0'
down_revision = ('add_decline_fields', 'remove_vendor_rooms_columns')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass