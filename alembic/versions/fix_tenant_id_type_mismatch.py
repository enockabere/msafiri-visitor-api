"""Fix accommodation tables tenant_id type mismatch

Revision ID: fix_tenant_id_type_mismatch
Revises: add_decline_tracking_fields
Create Date: 2024-12-04 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_tenant_id_type_mismatch'
down_revision = 'add_decline_tracking_fields'
branch_labels = None
depends_on = None

def fix_table_tenant_id(table_name, index_name):
    """Helper function to fix tenant_id type for a table"""
    try:
        # Check if table exists and has string tenant_id
        result = op.get_bind().execute(sa.text(f"""
            SELECT data_type FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = 'tenant_id'
        """)).fetchone()
        
        if not result or result[0] == 'integer':
            return  # Already fixed or doesn't exist
        
        # Step 1: Add a temporary column for the new integer tenant_id
        op.add_column(table_name, sa.Column('tenant_id_new', sa.Integer(), nullable=True))
        
        # Step 2: Update the new column with integer values by looking up tenant slugs
        op.execute(f"""
            UPDATE {table_name} 
            SET tenant_id_new = tenants.id 
            FROM tenants 
            WHERE {table_name}.tenant_id = tenants.slug
        """)
        
        # Step 3: For any records that couldn't be mapped, try to find a default tenant
        op.execute(f"""
            UPDATE {table_name} 
            SET tenant_id_new = (SELECT id FROM tenants ORDER BY id LIMIT 1)
            WHERE tenant_id_new IS NULL
        """)
        
        # Step 4: Drop the old tenant_id column and its index
        try:
            op.drop_index(index_name, table_name=table_name)
        except:
            pass  # Index might not exist
        op.drop_column(table_name, 'tenant_id')
        
        # Step 5: Rename the new column to tenant_id
        op.alter_column(table_name, 'tenant_id_new', new_column_name='tenant_id')
        
        # Step 6: Make the column non-nullable
        op.alter_column(table_name, 'tenant_id', nullable=False)
        
        # Step 7: Recreate the index
        op.create_index(index_name, table_name, ['tenant_id'], unique=False)
        
    except Exception as e:
        print(f"Error fixing {table_name}: {e}")

def upgrade():
    # Fix accommodation_allocations table
    fix_table_tenant_id('accommodation_allocations', 'ix_accommodation_allocations_tenant_id')
    
    # Fix guesthouses table
    fix_table_tenant_id('guesthouses', 'ix_guesthouses_tenant_id')
    
    # Fix rooms table
    fix_table_tenant_id('rooms', 'ix_rooms_tenant_id')
    
    # Fix vendor_accommodations table
    fix_table_tenant_id('vendor_accommodations', 'ix_vendor_accommodations_tenant_id')
    
    # Fix vendor_event_accommodations table
    fix_table_tenant_id('vendor_event_accommodations', 'ix_vendor_event_accommodations_tenant_id')

def downgrade():
    # This migration is not reversible as it involves data type conversion
    pass