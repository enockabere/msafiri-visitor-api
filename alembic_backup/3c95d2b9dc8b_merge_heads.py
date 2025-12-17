"""merge heads

Revision ID: 3c95d2b9dc8b
Revises: add_guest_house_contact_fields, create_chat_rooms
Create Date: 2025-10-27 09:19:14.953881

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c95d2b9dc8b'
down_revision = ('add_guest_house_contact_fields', 'create_chat_rooms')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass