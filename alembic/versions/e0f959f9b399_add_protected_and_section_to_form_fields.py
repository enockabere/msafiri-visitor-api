"""add_protected_and_section_to_form_fields

Revision ID: e0f959f9b399
Revises: e2100976e073
Create Date: 2025-12-16 14:19:56.305915

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0f959f9b399'
down_revision = 'e2100976e073'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to form_fields table
    op.add_column('form_fields', sa.Column('is_protected', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('form_fields', sa.Column('section', sa.String(50), nullable=True))


def downgrade() -> None:
    # Remove columns if rolling back
    op.drop_column('form_fields', 'section')
    op.drop_column('form_fields', 'is_protected')