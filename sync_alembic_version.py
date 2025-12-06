#!/usr/bin/env python3
"""
Script to sync the alembic_version table with actual database state.
This fixes the issue where migrations show as "applied" but tables don't exist.
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://msafiri_user:password%401234@localhost:5432/msafiri_db"
)

def check_tables_and_suggest_version():
    """Check which tables exist and suggest the correct alembic version."""

    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    print(f"📊 Found {len(existing_tables)} tables in database")

    # Key tables to check
    key_tables = {
        'flight_itineraries': '148b242d4e59',  # create_flight_itineraries_table
        'transport_requests': 'create_transport_requests',  # create_transport_requests_table
        'travel_checklist_progress': 'f1895cdab0c6',  # ensure_travel_checklist_progress_table
    }

    print("\n🔍 Checking key tables:")
    missing_tables = []
    for table_name, migration_id in key_tables.items():
        exists = table_name in existing_tables
        status = "✅" if exists else "❌"
        print(f"  {status} {table_name} - Migration: {migration_id}")
        if not exists:
            missing_tables.append(table_name)

    # Check current alembic version
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            print(f"\n📌 Current alembic_version: {current_version}")
    except Exception as e:
        print(f"\n⚠️  Could not read alembic_version: {e}")
        current_version = None

    if missing_tables:
        print(f"\n❌ Missing tables detected: {', '.join(missing_tables)}")
        print("\n💡 Recommended actions:")
        print("   1. Run: python check_and_create_missing_tables.py")
        print("   2. Then run: alembic stamp head")
        print("   3. Or use the function below to manually stamp")
        return False
    else:
        print("\n✅ All key tables exist!")
        if current_version:
            print(f"✅ Database appears to be in sync (version: {current_version})")
        return True

    engine.dispose()

def stamp_to_head():
    """Stamp the database to head after tables are created."""
    engine = create_engine(DATABASE_URL)

    print("\n🔧 Stamping database to 'head'...")

    try:
        # This updates the alembic_version table to reflect current state
        import subprocess
        result = subprocess.run(
            ['alembic', 'stamp', 'head'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.returncode == 0:
            print("✅ Database stamped to head successfully!")
            print(result.stdout)
        else:
            print(f"❌ Error stamping database: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        engine.dispose()

    return True

def main():
    print("=" * 70)
    print("🔍 Alembic Version Sync Check")
    print("=" * 70)
    print()

    # Check current state
    tables_ok = check_tables_and_suggest_version()

    if tables_ok:
        print("\n" + "=" * 70)
        print("✅ Database is in good state!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠️  Action required: Create missing tables first")
        print("=" * 70)

if __name__ == "__main__":
    main()
