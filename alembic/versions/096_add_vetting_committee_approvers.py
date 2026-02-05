# File: alembic/versions/096_add_vetting_committee_approvers.py
"""Add vetting committee approvers table

Revision ID: 096_add_vetting_committee_approvers
Revises: 095_add_voucher_type_to_allocations
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '096_add_vetting_committee_approvers'
down_revision = '095_add_voucher_type_to_allocations'
branch_labels = None
depends_on = None

def upgrade():
    # Create vetting_committee_approvers table
    op.create_table('vetting_committee_approvers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('committee_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('invitation_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invitation_token', sa.String(length=255), nullable=True),
        sa.Column('first_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('had_previous_role', sa.String(length=50), nullable=True),
        sa.Column('role_removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['committee_id'], ['vetting_committees.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Make approver_email nullable in vetting_committees table for backward compatibility
    op.alter_column('vetting_committees', 'approver_email',
                    existing_type=sa.String(length=255),
                    nullable=True)

def downgrade():
    # Make approver_email non-nullable again
    op.alter_column('vetting_committees', 'approver_email',
                    existing_type=sa.String(length=255),
                    nullable=False)
    
    # Drop vetting_committee_approvers table
    op.drop_table('vetting_committee_approvers')