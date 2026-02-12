"""Add acceptance status to travel request travelers

Revision ID: 2025_02_12_acceptance
Revises: bbee329c2282
Create Date: 2025-02-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_12_acceptance'
down_revision = 'bbee329c2282'
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

    # Check if travel_request_approvals table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'travel_request_approvals' not in inspector.get_table_names():
        # Create approval action enum only if table doesn't exist
        approval_action_type = sa.Enum('approved', 'rejected', name='approvalactiontype')
        approval_action_type.create(op.get_bind(), checkfirst=True)

        # Create travel_request_approvals table
        op.create_table('travel_request_approvals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('travel_request_id', sa.Integer(), nullable=False),
            sa.Column('step_number', sa.Integer(), nullable=False),
            sa.Column('step_name', sa.String(255), nullable=True),
            sa.Column('approver_id', sa.Integer(), nullable=False),
            sa.Column('action', sa.Enum('approved', 'rejected', name='approvalactiontype'), nullable=False),
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
    # Check if travel_request_approvals table exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'travel_request_approvals' in inspector.get_table_names():
        # Drop travel_request_approvals table
        op.drop_index('ix_travel_request_approvals_approver_id', table_name='travel_request_approvals')
        op.drop_index('ix_travel_request_approvals_travel_request_id', table_name='travel_request_approvals')
        op.drop_table('travel_request_approvals')

        # Drop approval action enum
        op.execute('DROP TYPE IF EXISTS approvalactiontype')

    # Drop columns from travel_request_travelers
    op.drop_column('travel_request_travelers', 'decline_reason')
    op.drop_column('travel_request_travelers', 'declined_at')
    op.drop_column('travel_request_travelers', 'accepted_at')
    op.drop_column('travel_request_travelers', 'acceptance_status')

    # Drop traveler acceptance status enum
    op.execute('DROP TYPE IF EXISTS traveleracceptancestatus')
