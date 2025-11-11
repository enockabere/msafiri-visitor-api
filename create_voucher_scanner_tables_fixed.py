#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_voucher_scanner_tables():
    """Create tables for voucher scanner functionality"""
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        try:
            print("Creating voucher scanner tables...")
            
            # Get first tenant ID
            tenant_result = connection.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1;"))
            tenant_row = tenant_result.fetchone()
            
            if not tenant_row:
                print("❌ No tenants found. Please create a tenant first.")
                return
            
            tenant_id = tenant_row[0]
            print(f"Using tenant ID: {tenant_id}")
            
            # Check if voucher_scanner role exists
            role_result = connection.execute(text("""
                SELECT id FROM roles WHERE name = 'voucher_scanner' AND tenant_id = :tenant_id LIMIT 1;
            """), {"tenant_id": tenant_id})
            
            if not role_result.fetchone():
                connection.execute(text("""
                    INSERT INTO roles (name, description, tenant_id, created_at, updated_at)
                    VALUES ('voucher_scanner', 'Can scan and redeem vouchers', :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """), {"tenant_id": tenant_id})
                print("✅ Created voucher_scanner role")
            else:
                print("✅ voucher_scanner role already exists")
            
            # Commit the role creation
            connection.commit()
            
            print("✅ Voucher scanner setup completed successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            connection.rollback()
            raise e

if __name__ == "__main__":
    create_voucher_scanner_tables()