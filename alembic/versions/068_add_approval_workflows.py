"""add approval workflows

Revision ID: 068_add_approval_workflows
Revises: update_perdiem_status_enum
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '068_add_approval_workflows'
down_revision = 'update_perdiem_status_enum'
branch_labels = None
depends_on = None

def upgrade():
    # Create approval_workflows table
    op.create_table(
        'approval_workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('workflow_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_workflows_id'), 'approval_workflows', ['id'], unique=False)
    op.create_index(op.f('ix_approval_workflows_tenant_id'), 'approval_workflows', ['tenant_id'], unique=False)

    # Create approval_steps table
    op.create_table(
        'approval_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(length=255), nullable=True),
        sa.Column('approver_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['approval_workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approval_steps_id'), 'approval_steps', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_approval_steps_id'), table_name='approval_steps')
    op.drop_table('approval_steps')
    op.drop_index(op.f('ix_approval_workflows_tenant_id'), table_name='approval_workflows')
    op.drop_index(op.f('ix_approval_workflows_id'), table_name='approval_workflows')
    op.drop_table('approval_workflows')
