"""Add vetting_role_assignments table

Revision ID: 027_add_vetting_role_assignments
Revises: 026_add_vetting_approver_to_enum
Create Date: 2025-01-05 01:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '027_add_vetting_role_assignments'
down_revision = '026_add_vetting_approver_to_enum'
branch_labels = None
depends_on = None

def upgrade():
    # Create vetting_role_assignments table
    op.create_table('vetting_role_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('role_type', sa.String(50), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_vetting_role_assignments_user_id', 'vetting_role_assignments', ['user_id'])
    op.create_index('idx_vetting_role_assignments_committee_id', 'vetting_role_assignments', ['committee_id'])

def downgrade():
    op.drop_table('vetting_role_assignments')