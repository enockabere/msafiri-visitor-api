"""ensure travel checklist progress table exists

Revision ID: f1895cdab0c6
Revises: 8b03268ec634
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1895cdab0c6'
down_revision = '8b03268ec634'
branch_labels = None
depends_on = None

def upgrade():
    # Create travel_checklist_progress table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS travel_checklist_progress (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            checklist_items JSONB,
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, user_email)
        );
    """)

def downgrade():
    op.drop_table('travel_checklist_progress')