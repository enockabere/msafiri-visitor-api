"""add travel request approvals table

Revision ID: 103_add_travel_request_approvals
Revises: 102_add_vetting_member_submissions
Create Date: 2025-02-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '103_add_travel_request_approvals'
down_revision = '102_add_vetting_member_submissions'
branch_labels = None
depends_on = None


def upgrade():
    # Create travel_request_approval_steps table
    op.create_table(
        'travel_request_approval_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('travel_request_id', sa.Integer(), nullable=False),
        sa.Column('workflow_step_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('approver_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('budget_code', sa.String(100), nullable=True),
        sa.Column('activity_code', sa.String(100), nullable=True),
        sa.Column('cost_center', sa.String(100), nullable=True),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['travel_request_id'], ['travel_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_step_id'], ['approval_steps.id']),
        sa.ForeignKeyConstraint(['approver_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_travel_request_approval_steps_travel_request_id', 'travel_request_approval_steps', ['travel_request_id'])
    op.create_index('ix_travel_request_approval_steps_approver_user_id', 'travel_request_approval_steps', ['approver_user_id'])


def downgrade():
    op.drop_index('ix_travel_request_approval_steps_approver_user_id')
    op.drop_index('ix_travel_request_approval_steps_travel_request_id')
    op.drop_table('travel_request_approval_steps')
