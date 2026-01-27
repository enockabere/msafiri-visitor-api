"""update_perdiem_approver_fields

Revision ID: 049_update_perdiem_approver_fields
Revises: 048_add_purpose_to_perdiem
Create Date: 2025-01-27 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '049_update_perdiem_approver_fields'
down_revision = '048_add_purpose_to_perdiem'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add approver fields
    op.add_column('perdiem_requests', sa.Column('approver_title', sa.String(50), nullable=True))
    op.add_column('perdiem_requests', sa.Column('approver_email', sa.String(255), nullable=True))

def downgrade() -> None:
    # Remove approver fields
    op.drop_column('perdiem_requests', 'approver_email')
    op.drop_column('perdiem_requests', 'approver_title')