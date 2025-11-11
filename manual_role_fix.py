#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_role():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        try:
            # Get tenant info to see the data type
            tenant_result = connection.execute(text("SELECT id, slug FROM tenants ORDER BY id LIMIT 1;"))
            tenant_row = tenant_result.fetchone()
            
            if not tenant_row:
                print("❌ No tenants found")
                return
            
            tenant_id = str(tenant_row[0])  # Convert to string
            print(f"Using tenant ID: {tenant_id} (slug: {tenant_row[1]})")
            
            # Check if role exists (without tenant_id filter first)
            role_result = connection.execute(text("SELECT id, tenant_id FROM roles WHERE name = 'voucher_scanner';"))
            existing_role = role_result.fetchone()
            
            if existing_role:
                print(f"✅ voucher_scanner role already exists (ID: {existing_role[0]}, tenant_id: {existing_role[1]})")
                return
            
            # Create the role
            connection.execute(text("""
                INSERT INTO roles (name, description, tenant_id, created_at, updated_at)
                VALUES ('voucher_scanner', 'Can scan and redeem vouchers', :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """), {"tenant_id": tenant_id})
            
            connection.commit()
            print("✅ Created voucher_scanner role successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            connection.rollback()

if __name__ == "__main__":
    create_role()