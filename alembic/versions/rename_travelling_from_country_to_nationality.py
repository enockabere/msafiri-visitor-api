"""Rename travelling_from_country to nationality

Revision ID: rename_travelling_from_country_to_nationality
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rename_travelling_from_country_to_nationality'
down_revision = None  # Update this with the latest revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Rename the column from travelling_from_country to nationality
    op.alter_column('event_participants', 'travelling_from_country', new_column_name='nationality')


def downgrade():
    # Rename the column back from nationality to travelling_from_country
    op.alter_column('event_participants', 'nationality', new_column_name='travelling_from_country')