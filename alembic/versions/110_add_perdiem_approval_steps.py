"""add perdiem approval steps

Revision ID: 110_add_perdiem_approval_steps
Revises: 108
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '110_add_perdiem_approval_steps'
down_revision = '108'
branch_labels = None
depends_on = None

def upgrade():
    # Create perdiem_approval_steps table
    op.create_table(
        'perdiem_approval_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('perdiem_request_id', sa.Integer(), nullable=False),
        sa.Column('workflow_step_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('approver_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['perdiem_request_id'], ['perdiem_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_step_id'], ['approval_steps.id'], ),
        sa.ForeignKeyConstraint(['approver_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_perdiem_approval_steps_id'), 'perdiem_approval_steps', ['id'], unique=False)
    op.create_index(op.f('ix_perdiem_approval_steps_perdiem_request_id'), 'perdiem_approval_steps', ['perdiem_request_id'], unique=False)
    op.create_index(op.f('ix_perdiem_approval_steps_approver_user_id'), 'perdiem_approval_steps', ['approver_user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_perdiem_approval_steps_approver_user_id'), table_name='perdiem_approval_steps')
    op.drop_index(op.f('ix_perdiem_approval_steps_perdiem_request_id'), table_name='perdiem_approval_steps')
    op.drop_index(op.f('ix_perdiem_approval_steps_id'), table_name='perdiem_approval_steps')
    op.drop_table('perdiem_approval_steps')
