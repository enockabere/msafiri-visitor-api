"""add claim approvals table

Revision ID: add_claim_approvals
Revises: 
Create Date: 2024-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_claim_approvals'
down_revision = None  # Update this with your latest migration
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'claim_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('workflow_step_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('approver_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='PENDING'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ),
        sa.ForeignKeyConstraint(['workflow_step_id'], ['approval_workflow_steps.id'], ),
        sa.ForeignKeyConstraint(['approver_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_claim_approvals_id'), 'claim_approvals', ['id'], unique=False)
    op.create_index(op.f('ix_claim_approvals_claim_id'), 'claim_approvals', ['claim_id'], unique=False)
    op.create_index(op.f('ix_claim_approvals_approver_user_id'), 'claim_approvals', ['approver_user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_claim_approvals_approver_user_id'), table_name='claim_approvals')
    op.drop_index(op.f('ix_claim_approvals_claim_id'), table_name='claim_approvals')
    op.drop_index(op.f('ix_claim_approvals_id'), table_name='claim_approvals')
    op.drop_table('claim_approvals')
