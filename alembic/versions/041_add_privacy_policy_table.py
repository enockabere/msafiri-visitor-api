"""Add privacy policy table

Revision ID: 041_add_privacy_policy_table
Revises: 040_add_user_roles_table
Create Date: 2024-01-01 00:00:00.000000

Adds privacy_policies table for super admin management of privacy policy documents.
Includes audit trail with created_by/updated_by fields storing super admin emails.

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '041_add_privacy_policy_table'
down_revision = '040_add_user_roles_table'
branch_labels = None
depends_on = None

def upgrade():
    # Create privacy_policies table
    op.create_table(
        'privacy_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False, server_default='Privacy Policy'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('document_url', sa.String(500), nullable=True),
        sa.Column('document_public_id', sa.String(255), nullable=True),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(255), nullable=False),  # Super admin email
        sa.Column('updated_by', sa.String(255), nullable=True),   # Super admin email
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on is_active for faster queries
    op.create_index('ix_privacy_policies_is_active', 'privacy_policies', ['is_active'])
    
    # Create index on created_at for audit queries
    op.create_index('ix_privacy_policies_created_at', 'privacy_policies', ['created_at'])

def downgrade():
    op.drop_index('ix_privacy_policies_created_at', table_name='privacy_policies')
    op.drop_index('ix_privacy_policies_is_active', table_name='privacy_policies')
    op.drop_table('privacy_policies')