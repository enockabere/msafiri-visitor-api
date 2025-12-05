"""Remove description column from guesthouses

Revision ID: remove_description_guesthouses_fix
Revises: simple_add_app_feedback_enum
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_description_guesthouses_fix'
down_revision = 'simple_add_app_feedback_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Remove description column from guesthouses table
    op.drop_column('guesthouses', 'description')


def downgrade():
    # Add description column back to guesthouses table
    op.add_column('guesthouses', sa.Column('description', sa.Text(), nullable=True))
