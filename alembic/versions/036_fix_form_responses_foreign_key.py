"""fix form responses foreign key

Revision ID: 036_fix_form_responses_foreign_key
Revises: 035_add_budget_account_code_to_events
Create Date: 2025-01-17 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '036_fix_form_responses_foreign_key'
down_revision = '035_add_budget_account_code'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing foreign key constraint if it exists
    try:
        op.drop_constraint('form_responses_registration_id_fkey', 'form_responses', type_='foreignkey')
    except:
        pass  # Constraint might not exist
    
    # Add new foreign key constraint to event_participants table
    op.create_foreign_key(
        'form_responses_registration_id_fkey',
        'form_responses', 'event_participants',
        ['registration_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    # Drop the foreign key constraint
    op.drop_constraint('form_responses_registration_id_fkey', 'form_responses', type_='foreignkey')