#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.core.config import settings
    db_url = settings.DATABASE_URL
except ImportError:
    # Fallback to environment variable
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/msafiri_visitor_db')

print(f"Connecting to database...")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Check if timezone column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tenants' AND column_name = 'timezone'
        """))
        exists = result.fetchone()
        
        if not exists:
            print("Adding timezone column to tenants table...")
            conn.execute(text("ALTER TABLE tenants ADD COLUMN timezone VARCHAR(50)"))
            conn.commit()
            print("SUCCESS: Added timezone column successfully")
        else:
            print("INFO: Timezone column already exists")
        
        # Update MSF OCA tenant with timezone
        result = conn.execute(text("""
            UPDATE tenants 
            SET timezone = 'Africa/Nairobi' 
            WHERE slug = 'msf-oca' AND (timezone IS NULL OR timezone = '')
        """))
        
        if result.rowcount > 0:
            conn.commit()
            print("SUCCESS: Updated MSF OCA with Africa/Nairobi timezone")
        else:
            print("INFO: MSF OCA timezone already set or tenant not found")
        
        # Show current tenants with timezones
        result = conn.execute(text("SELECT slug, country, timezone FROM tenants"))
        tenants = result.fetchall()
        print("\nCurrent tenants:")
        for tenant in tenants:
            print(f"  {tenant.slug}: {tenant.country} -> {tenant.timezone or 'Not set'}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nSUCCESS: Migration completed successfully!")