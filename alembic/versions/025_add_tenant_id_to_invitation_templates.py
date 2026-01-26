"""add_tenant_id_to_invitation_templates

Revision ID: 025_add_tenant_id_to_invitation_templates
Revises: 024_invitation_templates
Create Date: 2025-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '025_add_tenant_id_to_invitation_templates'
down_revision = '024_invitation_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column to invitation_templates table
    op.add_column('invitation_templates', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_invitation_templates_tenant_id',
        'invitation_templates', 'tenants',
        ['tenant_id'], ['id']
    )
    
    # Create index for better performance
    op.create_index('ix_invitation_templates_tenant_id', 'invitation_templates', ['tenant_id'])
    
    # Set tenant_id to 1 for existing records (assuming first tenant exists)
    op.execute("UPDATE invitation_templates SET tenant_id = 1 WHERE tenant_id IS NULL")
    
    # Make tenant_id NOT NULL after setting default values
    op.alter_column('invitation_templates', 'tenant_id', nullable=False)


def downgrade():
    # Remove index
    op.drop_index('ix_invitation_templates_tenant_id', table_name='invitation_templates')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_invitation_templates_tenant_id', 'invitation_templates', type_='foreignkey')
    
    # Remove tenant_id column
    op.drop_column('invitation_templates', 'tenant_id')