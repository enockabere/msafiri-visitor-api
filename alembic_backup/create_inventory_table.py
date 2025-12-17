"""create inventory table

Revision ID: create_inventory_table
Revises: fix_tenant_id_type_mismatch
Create Date: 2024-12-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_inventory_table'
down_revision = 'fix_tenant_id_type_mismatch'
branch_labels = None
depends_on = None


def upgrade():
    # Create inventory table
    op.create_table('inventory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('condition', sa.String(length=50), nullable=True, server_default='good'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_tenant_id'), 'inventory', ['tenant_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_inventory_tenant_id'), table_name='inventory')
    op.drop_table('inventory')
