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
        # Create approval action enum only if it doesn't exist
        conn.execute(sa.text(
            "CREATE TYPE IF NOT EXISTS approvalactiontype AS ENUM ('approved', 'rejected')"
        ))

        # Create travel_request_approvals table using raw SQL to avoid enum recreation
        conn.execute(sa.text("""
            CREATE TABLE travel_request_approvals (
                id SERIAL PRIMARY KEY,
                travel_request_id INTEGER NOT NULL REFERENCES travel_requests(id) ON DELETE CASCADE,
                step_number INTEGER NOT NULL,
                step_name VARCHAR(255),
                approver_id INTEGER NOT NULL REFERENCES users(id),
                action approvalactiontype NOT NULL,
                comments TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        
        conn.execute(sa.text(
            "CREATE INDEX ix_travel_request_approvals_travel_request_id ON travel_request_approvals(travel_request_id)"
        ))
        conn.execute(sa.text(
            "CREATE INDEX ix_travel_request_approvals_approver_id ON travel_request_approvals(approver_id)"
        ))


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
