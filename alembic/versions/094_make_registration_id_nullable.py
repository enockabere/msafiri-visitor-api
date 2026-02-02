"""make registration_id nullable in line_manager_recommendations

Revision ID: 094_make_registration_id_nullable
Revises: 093_add_app_feedback_table
Create Date: 2026-02-02 14:06:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '094_make_registration_id_nullable'
down_revision = '093_add_app_feedback_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Make registration_id nullable
    op.alter_column('line_manager_recommendations', 'registration_id',
                   existing_type=sa.Integer(),
                   nullable=True)

def downgrade() -> None:
    # Make registration_id not nullable again
    op.alter_column('line_manager_recommendations', 'registration_id',
                   existing_type=sa.Integer(),
                   nullable=False)