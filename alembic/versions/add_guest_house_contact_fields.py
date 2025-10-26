"""add guest house contact fields

Revision ID: add_guest_house_contact_fields
Revises: create_guest_house_tables
Create Date: 2024-10-26 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_guest_house_contact_fields'
down_revision = 'create_guest_house_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to guesthouses table
    op.add_column('guesthouses', sa.Column('contact_person', sa.String(200), nullable=True))
    op.add_column('guesthouses', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('guesthouses', sa.Column('email', sa.String(100), nullable=True))
    op.add_column('guesthouses', sa.Column('facilities', sa.Text(), nullable=True))
    op.add_column('guesthouses', sa.Column('house_rules', sa.Text(), nullable=True))
    op.add_column('guesthouses', sa.Column('check_in_time', sa.String(10), nullable=True))
    op.add_column('guesthouses', sa.Column('check_out_time', sa.String(10), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('guesthouses', 'check_out_time')
    op.drop_column('guesthouses', 'check_in_time')
    op.drop_column('guesthouses', 'house_rules')
    op.drop_column('guesthouses', 'facilities')
    op.drop_column('guesthouses', 'email')
    op.drop_column('guesthouses', 'phone')
    op.drop_column('guesthouses', 'contact_person')