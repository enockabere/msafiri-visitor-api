#!/usr/bin/env python3
"""
Create event_voucher_scanners table for event-specific scanner tracking
This fixes the issue where voucher scanners appear across all events in the same tenant
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'msafiri_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def create_event_voucher_scanners_table():
    """Create event_voucher_scanners table for event-specific scanner tracking"""
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Creating event_voucher_scanners table...")
        
        # Create the table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS event_voucher_scanners (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            tenant_id INTEGER NOT NULL,
            created_by VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(user_id, event_id)
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Create indexes for better performance
        create_indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_event_id ON event_voucher_scanners(event_id);",
            "CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_user_id ON event_voucher_scanners(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_tenant_id ON event_voucher_scanners(tenant_id);",
            "CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_active ON event_voucher_scanners(is_active);"
        ]
        
        for index_sql in create_indexes_sql:
            cursor.execute(index_sql)
        
        # Commit changes
        conn.commit()
        
        print("SUCCESS: event_voucher_scanners table created successfully!")
        print("SUCCESS: Indexes created successfully!")
        
        # Verify table creation
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'event_voucher_scanners'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print(f"\nTable structure ({len(columns)} columns):")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"  - {col['column_name']}: {col['data_type']} {nullable}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error creating event_voucher_scanners table: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function"""
    print("Creating event_voucher_scanners table for event-specific scanner tracking...")
    print("=" * 80)
    
    success = create_event_voucher_scanners_table()
    
    print("=" * 80)
    if success:
        print("SUCCESS: Event voucher scanners table setup completed successfully!")
        print("\nThis fixes the issue where:")
        print("   - Voucher scanners from Event 1 appeared in Event 2")
        print("   - Scanners were tenant-scoped instead of event-scoped")
        print("   - New events automatically showed existing scanners")
    else:
        print("ERROR: Event voucher scanners table setup failed!")

if __name__ == "__main__":
    main()