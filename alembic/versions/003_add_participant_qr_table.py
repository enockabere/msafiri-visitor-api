"""Add participant QR codes table

Revision ID: 003_add_participant_qr_table
Revises: 002_add_registration_form_fields
Create Date: 2024-10-09 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_participant_qr_table'
down_revision = '002_add_registration_form_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Create participant_qr_codes table
    op.create_table(
        'participant_qr_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('qr_token', sa.String(255), nullable=False),
        sa.Column('qr_data', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['participant_id'], ['event_participants.id']),
        sa.UniqueConstraint('participant_id'),
        sa.UniqueConstraint('qr_token')
    )
    op.create_index('ix_participant_qr_codes_id', 'participant_qr_codes', ['id'])

def downgrade():
    op.drop_index('ix_participant_qr_codes_id', 'participant_qr_codes')
    op.drop_table('participant_qr_codes')