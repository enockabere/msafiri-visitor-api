#!/usr/bin/env bash

set -o errexit  # Exit on error

echo "🔄 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔍 Checking if migration is needed..."
if python -c "
import sys, os
sys.path.append('.')
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'date_of_birth'
            )
        '''))
        if result.scalar():
            print('SKIP_MIGRATION')
            sys.exit(0)
        else:
            print('RUN_MIGRATION')
            sys.exit(1)
except Exception as e:
    print(f'Error checking database: {e}')
    print('RUN_MIGRATION')
    sys.exit(1)
"; then
    echo "✅ Enhanced columns already exist - skipping migration"
    echo "📋 Marking migration as completed..."
    
    # Mark the migration as completed to avoid future conflicts
    python -c "
import sys, os
sys.path.append('.')
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text('''
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        '''))
        
        if result.scalar():
            # Update to latest migration
            conn.execute(text('''
                UPDATE alembic_version 
                SET version_num = 'enhanced_profile_safe'
            '''))
            conn.commit()
            print('✅ Migration version updated')
        else:
            # Create alembic_version table
            conn.execute(text('''
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            '''))
            conn.execute(text('''
                INSERT INTO alembic_version (version_num) 
                VALUES ('enhanced_profile_safe')
            '''))
            conn.commit()
            print('✅ Alembic version table created')
            
except Exception as e:
    print(f'Warning: Could not update migration version: {e}')
"
else
    echo "📋 Running database migrations..."
    
    # Try to run migration, but don't fail if columns already exist
    if ! alembic upgrade head 2>&1 | tee migration.log; then
        echo "⚠️  Migration failed, checking if it's due to existing columns..."
        
        if grep -q "already exists" migration.log || grep -q "DuplicateColumn" migration.log; then
            echo "✅ Columns already exist - marking migration as completed"
            
            python -c "
import sys, os
sys.path.append('.')
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text('''
            UPDATE alembic_version 
            SET version_num = 'enhanced_profile_safe'
        '''))
        conn.commit()
        print('✅ Migration marked as completed')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"
        else
            echo "❌ Migration failed for other reasons"
            cat migration.log
            exit 1
        fi
    else
        echo "✅ Migration completed successfully!"
    fi
fi

# Clean up
rm -f migration.log

echo "✅ Build completed successfully!"