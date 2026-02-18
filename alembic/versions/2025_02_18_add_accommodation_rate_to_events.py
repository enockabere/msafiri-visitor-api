"""Add accommodation rate fields to events

Revision ID: 7a8b9c0d1e2f
Revises:
Create Date: 2025-02-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add accommodation_rate_per_day column to events table
    op.add_column('events',
        sa.Column('accommodation_rate_per_day', sa.Numeric(10, 2), nullable=True)
    )

    # Add accommodation_rate_currency column to events table
    op.add_column('events',
        sa.Column('accommodation_rate_currency', sa.String(3), nullable=True, server_default='KES')
    )


def downgrade() -> None:
    op.drop_column('events', 'accommodation_rate_currency')
    op.drop_column('events', 'accommodation_rate_per_day')
