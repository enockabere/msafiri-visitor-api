"""merge form fields with main

Revision ID: eb4e20311ce2
Revises: 18c343ad19c2, create_dynamic_form_fields
Create Date: 2025-12-14 10:45:10.016324

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb4e20311ce2'
down_revision = ('18c343ad19c2', 'create_dynamic_form_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass