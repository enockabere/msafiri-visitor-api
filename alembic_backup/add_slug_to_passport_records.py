"""Add slug column to passport_records table

Revision ID: add_slug_to_passport_records
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import hashlib
import secrets

# revision identifiers, used by Alembic.
revision = 'add_slug_to_passport_records'
down_revision = None  # Update this to the latest revision ID
branch_labels = None
depends_on = None

def upgrade():
    # Add slug column to passport_records table
    op.add_column('passport_records', sa.Column('slug', sa.String(), nullable=True))
    
    # Create unique index on slug column
    op.create_index('ix_passport_records_slug', 'passport_records', ['slug'], unique=True)
    
    # Generate slugs for existing records
    connection = op.get_bind()
    
    # Get all existing passport records
    result = connection.execute(sa.text("""
        SELECT id, record_id, user_email 
        FROM passport_records 
        WHERE slug IS NULL
    """))
    
    records = result.fetchall()
    
    # Generate and update slugs for existing records
    for record in records:
        # Generate slug similar to the model method
        salt = secrets.token_hex(8)
        data = f"{record.record_id}-{record.user_email}-{salt}"
        slug = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        # Update the record with the generated slug
        connection.execute(sa.text("""
            UPDATE passport_records 
            SET slug = :slug 
            WHERE id = :record_id
        """), {"slug": slug, "record_id": record.id})

def downgrade():
    # Remove the index first
    op.drop_index('ix_passport_records_slug', table_name='passport_records')
    
    # Remove the slug column
    op.drop_column('passport_records', 'slug')