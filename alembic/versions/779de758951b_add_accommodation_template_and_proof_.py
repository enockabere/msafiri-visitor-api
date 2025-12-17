"""add_accommodation_template_and_proof_fields

Revision ID: 779de758951b
Revises: 4c8f57e5312c
Create Date: 2025-12-12 15:09:24.705232

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '779de758951b'
down_revision = '4c8f57e5312c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add accommodation_template field to vendor_accommodations table
    op.add_column('vendor_accommodations',
        sa.Column('accommodation_template', sa.Text(), nullable=True)
    )

    # Add proof_of_accommodation_url field to event_participants table
    op.add_column('event_participants',
        sa.Column('proof_of_accommodation_url', sa.String(500), nullable=True)
    )

    # Add proof_generated_at timestamp to track when proof was generated
    op.add_column('event_participants',
        sa.Column('proof_generated_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    # Remove fields in reverse order
    op.drop_column('event_participants', 'proof_generated_at')
    op.drop_column('event_participants', 'proof_of_accommodation_url')
    op.drop_column('vendor_accommodations', 'accommodation_template')