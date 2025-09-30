import psycopg2
import sys

def migrate_allocations_table():
    conn = None
    cursor = None
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="msafiri_visitor_db",
            user="postgres",
            password="password"
        )
        
        cursor = conn.cursor()
        
        print("Updating event_allocations table structure...")
        
        # Drop old columns and add new ones
        cursor.execute("""
            ALTER TABLE event_allocations 
            DROP COLUMN IF EXISTS inventory_item_id,
            DROP COLUMN IF EXISTS quantity_per_participant,
            ADD COLUMN IF NOT EXISTS items JSONB,
            ADD COLUMN IF NOT EXISTS hr_notes TEXT,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """)
        
        # Update existing records
        cursor.execute("""
            UPDATE event_allocations 
            SET items = '[]'::jsonb 
            WHERE items IS NULL;
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_allocations_event_id ON event_allocations(event_id);
            CREATE INDEX IF NOT EXISTS idx_allocations_status ON event_allocations(status);
            CREATE INDEX IF NOT EXISTS idx_allocations_tenant_id ON event_allocations(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_allocations_items ON event_allocations USING GIN(items);
        """)
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_allocations_table()