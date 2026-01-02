"""fix_direct_messages_id_sequence

Revision ID: 086fix_dm_seq
Revises: 085532e32bfb
Create Date: 2025-01-22 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '086fix_dm_seq'
down_revision = '085532e32bfb'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Fix the direct_messages id column to ensure it's properly auto-incrementing
    # First, get the current max id
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT COALESCE(MAX(id), 0) FROM direct_messages"))
    max_id = result.scalar()
    
    # Reset the sequence to start from max_id + 1
    connection.execute(sa.text(f"SELECT setval('direct_messages_id_seq', {max_id + 1}, false)"))
    
    # Ensure the id column is properly configured as SERIAL
    op.execute("ALTER TABLE direct_messages ALTER COLUMN id SET DEFAULT nextval('direct_messages_id_seq')")

def downgrade() -> None:
    # No downgrade needed
    pass