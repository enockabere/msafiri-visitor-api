"""Add missing certificate_public_id column

Revision ID: 030_fix_participant_certificates
Revises: dd7f47274857
Create Date: 2026-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030_fix_participant_certificates'
down_revision = 'dd7f47274857'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('participant_certificates')]
    
    if 'certificate_public_id' not in columns:
        op.add_column('participant_certificates', 
                     sa.Column('certificate_public_id', sa.String(length=255), nullable=True))
    
    if 'email_sent' not in columns:
        op.add_column('participant_certificates', 
                     sa.Column('email_sent', sa.Boolean(), server_default='false', nullable=False))
    
    if 'email_sent_at' not in columns:
        op.add_column('participant_certificates', 
                     sa.Column('email_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('participant_certificates', 'email_sent_at')
    op.drop_column('participant_certificates', 'email_sent')
    op.drop_column('participant_certificates', 'certificate_public_id')
