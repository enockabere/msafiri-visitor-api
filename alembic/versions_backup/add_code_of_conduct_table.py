"""Add code of conduct table

Revision ID: add_code_of_conduct
Revises: 1bf3fe59ae7f
Create Date: 2024-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_code_of_conduct'
down_revision = '1bf3fe59ae7f'
branch_labels = None
depends_on = None

def upgrade():
    # Create code_of_conduct table
    op.create_table('code_of_conduct',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_code_of_conduct_tenant_id', 'code_of_conduct', ['tenant_id'])
    op.create_index('idx_code_of_conduct_active', 'code_of_conduct', ['tenant_id', 'is_active'])

def downgrade():
    op.drop_table('code_of_conduct')