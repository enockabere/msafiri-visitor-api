"""Add tenant_id to badge_templates

Revision ID: 042_add_tenant_id_to_badge_templates
Revises: 041_add_privacy_policy_table
Create Date: 2024-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042_add_tenant_id_to_badge_templates'
down_revision = '041_add_privacy_policy_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column to badge_templates table
    op.add_column('badge_templates', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # Set default tenant_id to 1 for existing records (assuming tenant with id=1 exists)
    op.execute("UPDATE badge_templates SET tenant_id = 1 WHERE tenant_id IS NULL")
    
    # Make tenant_id non-nullable
    op.alter_column('badge_templates', 'tenant_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key('fk_badge_templates_tenant_id', 'badge_templates', 'tenants', ['tenant_id'], ['id'])
    
    # Add index for better query performance
    op.create_index('ix_badge_templates_tenant_id', 'badge_templates', ['tenant_id'])


def downgrade():
    # Remove index
    op.drop_index('ix_badge_templates_tenant_id', 'badge_templates')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_badge_templates_tenant_id', 'badge_templates', type_='foreignkey')
    
    # Remove tenant_id column
    op.drop_column('badge_templates', 'tenant_id')