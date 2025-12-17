"""merge travel requirements and room planning heads

Revision ID: e40cbba5b37c
Revises: add_event_room_planning, dbe9f41486ae
Create Date: 2025-10-25 11:48:15.793447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e40cbba5b37c'
down_revision = ('add_event_room_planning', 'dbe9f41486ae')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass