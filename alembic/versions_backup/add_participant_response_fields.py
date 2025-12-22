"""Add participant response fields

Revision ID: add_participant_response
Revises: add_code_of_conduct
Create Date: 2024-12-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_participant_response'
down_revision = 'add_code_of_conduct'
branch_labels = None
depends_on = None

def upgrade():
    # Create decline reason enum
    decline_reason_enum = sa.Enum(
        'No Show',
        'Declined - Operational / Work Reasons',
        'Declined - Personal Reasons',
        'Cancelled - Operational Reasons',
        'Cancelled - Personal Reasons',
        'Cancelled - Prioritising Other Training',
        'Cancelled - Visa Rejected',
        'Cancelled - Visa Appointment Not Available',
        'Cancelled - Visa Issuing Took Too Long',
        'Cancelled - Visa Process Unfeasible',
        'Cancellation',
        name='declinereason'
    )
    decline_reason_enum.create(op.get_bind())
    
    # Update decline_reason column to use enum
    op.execute("ALTER TABLE event_participants ALTER COLUMN decline_reason TYPE declinereason USING decline_reason::declinereason")
    
    # Add confirmed_at column
    op.add_column('event_participants', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    # Remove confirmed_at column
    op.drop_column('event_participants', 'confirmed_at')
    
    # Revert decline_reason to text
    op.execute("ALTER TABLE event_participants ALTER COLUMN decline_reason TYPE TEXT")
    
    # Drop enum
    op.execute("DROP TYPE declinereason")