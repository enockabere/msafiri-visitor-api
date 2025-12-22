""""merge_code_of_conduct_url_and_vetting_workflow"

Revision ID: e2100976e073
Revises: add_url_to_code_of_conduct, enhance_vetting_workflow
Create Date: 2025-12-15 13:48:35.483619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2100976e073'
down_revision = ('add_url_to_code_of_conduct', 'enhance_vetting_workflow')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass