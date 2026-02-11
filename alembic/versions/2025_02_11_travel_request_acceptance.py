"""Add acceptance and approval workflow fields to travel requests

Revision ID: 2025_02_11_travel_acceptance
Revises: 2025_02_10_add_tenant_location
Create Date: 2025-02-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_11_travel_acceptance'
down_revision = '2025_02_10_add_tenant_location'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create TravelerAcceptanceStatus enum
    traveler_acceptance_status = sa.Enum(
        'pending', 'accepted', 'declined',
        name='traveleracceptancestatus'
    )
    traveler_acceptance_status.create(op.get_bind(), checkfirst=True)

    # Add acceptance columns to travel_request_travelers
    op.add_column('travel_request_travelers',
        sa.Column('acceptance_status', traveler_acceptance_status,
                  nullable=False, server_default='pending'))
    op.add_column('travel_request_travelers',
        sa.Column('accepted_at', sa.DateTime(), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('declined_at', sa.DateTime(), nullable=True))
    op.add_column('travel_request_travelers',
        sa.Column('decline_reason', sa.Text(), nullable=True))

    # Add workflow tracking columns to travel_requests
    op.add_column('travel_requests',
        sa.Column('workflow_id', sa.Integer(), nullable=True))
    op.add_column('travel_requests',
        sa.Column('current_approval_step', sa.Integer(), nullable=False, server_default='0'))

    # Add foreign key for workflow
    op.create_foreign_key(
        'fk_travel_requests_workflow_id',
        'travel_requests', 'approval_workflows',
        ['workflow_id'], ['id']
    )

    # Create approval action enum
    approval_action_type = sa.Enum('approved', 'rejected', name='approvalactiontype')
    approval_action_type.create(op.get_bind(), checkfirst=True)

    # Create travel_request_approvals table
    op.create_table('travel_request_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('travel_request_id', sa.Integer(), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('approver_id', sa.Integer(), nullable=False),
        sa.Column('action', approval_action_type, nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['travel_request_id'], ['travel_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'])
    )
    op.create_index('ix_travel_request_approvals_travel_request_id',
                    'travel_request_approvals', ['travel_request_id'])
    op.create_index('ix_travel_request_approvals_approver_id',
                    'travel_request_approvals', ['approver_id'])


def downgrade() -> None:
    # Drop travel_request_approvals table
    op.drop_index('ix_travel_request_approvals_approver_id')
    op.drop_index('ix_travel_request_approvals_travel_request_id')
    op.drop_table('travel_request_approvals')

    # Drop approval action enum
    op.execute('DROP TYPE IF EXISTS approvalactiontype')

    # Drop foreign key and columns from travel_requests
    op.drop_constraint('fk_travel_requests_workflow_id', 'travel_requests', type_='foreignkey')
    op.drop_column('travel_requests', 'current_approval_step')
    op.drop_column('travel_requests', 'workflow_id')

    # Drop columns from travel_request_travelers
    op.drop_column('travel_request_travelers', 'decline_reason')
    op.drop_column('travel_request_travelers', 'declined_at')
    op.drop_column('travel_request_travelers', 'accepted_at')
    op.drop_column('travel_request_travelers', 'acceptance_status')

    # Drop traveler acceptance status enum
    op.execute('DROP TYPE IF EXISTS traveleracceptancestatus')
