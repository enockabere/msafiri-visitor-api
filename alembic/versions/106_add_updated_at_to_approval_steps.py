"""add updated_at to approval steps

Revision ID: 106
Revises: 105
Create Date: 2025-02-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column to travel_request_approval_steps
    op.add_column('travel_request_approval_steps', 
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False)
    )


def downgrade():
    op.drop_column('travel_request_approval_steps', 'updated_at')
