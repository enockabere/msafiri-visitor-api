#!/usr/bin/env python3
"""Manual migration script"""

import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def run_migration():
    """Run the migration manually"""
    print("🔄 Running manual migration...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Create inventory table
                print("Creating inventory table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        category VARCHAR(100),
                        quantity INTEGER DEFAULT 0,
                        condition VARCHAR(50) DEFAULT 'good',
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create event_allocations table
                print("Creating event_allocations table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS event_allocations (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        inventory_item_id INTEGER REFERENCES inventory(id) ON DELETE SET NULL,
                        quantity_per_participant INTEGER DEFAULT 0,
                        drink_vouchers_per_participant INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'pending',
                        notes TEXT,
                        tenant_id INTEGER NOT NULL,
                        created_by VARCHAR(255),
                        approved_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        approved_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                
                # Fix existing tables if they have wrong data types
                print("Fixing data types...")
                try:
                    conn.execute(text("ALTER TABLE inventory ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER"))
                    print("Fixed inventory.tenant_id data type")
                except Exception as e:
                    print(f"inventory.tenant_id already correct or error: {e}")
                    
                try:
                    conn.execute(text("ALTER TABLE event_allocations ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER"))
                    print("Fixed event_allocations.tenant_id data type")
                except Exception as e:
                    print(f"event_allocations.tenant_id already correct or error: {e}")
                
                # Add country column to tenants
                print("Adding country column to tenants...")
                conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS country VARCHAR(100)"))
                
                # Create indexes
                print("Creating indexes...")
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_inventory_tenant_id ON inventory(tenant_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_event_allocations_event_id ON event_allocations(event_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_event_allocations_tenant_id ON event_allocations(tenant_id)"))
                
                trans.commit()
                print("✅ Migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()