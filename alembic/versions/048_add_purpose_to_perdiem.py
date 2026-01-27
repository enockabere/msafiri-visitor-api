"""add_purpose_to_perdiem

Revision ID: 048_add_purpose_to_perdiem
Revises: 6f9fe5933fd8
Create Date: 2025-01-27 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '048_add_purpose_to_perdiem'
down_revision = '6f9fe5933fd8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('perdiem_requests', sa.Column('purpose', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('perdiem_requests', 'purpose')