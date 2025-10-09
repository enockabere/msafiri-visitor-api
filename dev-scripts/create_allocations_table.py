# File: create_allocations_table.py
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_allocations_table():
    """Create the event_allocations table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS event_allocations (
        id SERIAL PRIMARY KEY,
        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
        inventory_item_id INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
        quantity_per_participant INTEGER NOT NULL DEFAULT 1,
        drink_vouchers_per_participant INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(50) NOT NULL DEFAULT 'pending',
        notes TEXT,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        created_by VARCHAR(255) NOT NULL,
        approved_by VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_event_allocations_event_id ON event_allocations(event_id);
    CREATE INDEX IF NOT EXISTS idx_event_allocations_tenant_id ON event_allocations(tenant_id);
    CREATE INDEX IF NOT EXISTS idx_event_allocations_status ON event_allocations(status);
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(create_table_sql))
            connection.commit()
            print("Event allocations table created successfully!")
            
    except Exception as e:
        print(f"Error creating event allocations table: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    create_allocations_table()