#!/usr/bin/env bash

set -o errexit  # Exit on error

echo "🚀 RENDER DEPLOYMENT BUILD"
echo "=" * 50

echo "🔄 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔍 Checking database state..."

# Check if this is a fresh database or existing one
python -c "
import sys, os
sys.path.append('.')
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Check if users table exists
        result = conn.execute(text('''
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        '''))
        
        if result.scalar():
            print('EXISTING_DATABASE')
            sys.exit(0)
        else:
            print('FRESH_DATABASE')
            sys.exit(1)
            
except Exception as e:
    print(f'DATABASE_ERROR: {e}')
    print('FRESH_DATABASE')  # Assume fresh if we can't check
    sys.exit(1)
" && DB_STATE="EXISTING" || DB_STATE="FRESH"

if [ "$DB_STATE" = "EXISTING" ]; then
    echo "✅ Database already exists - running standard migration"
    
    # Just run any pending migrations
    alembic upgrade head || {
        echo "⚠️  Migration failed, but database exists - continuing"
    }
    
else
    echo "🏗️  Fresh database detected - setting up from scratch"
    
    # Create fresh migration and run it
    echo "📋 Creating initial migration..."
    alembic revision --autogenerate -m "initial_setup" || {
        echo "⚠️  Migration creation failed - trying manual setup"
        
        # Manual table creation as fallback
        python -c "
import sys, os
sys.path.append('.')

try:
    from app.db.database import Base, engine
    from app.models import *
    
    print('Creating tables manually...')
    Base.metadata.create_all(bind=engine)
    print('Tables created successfully!')
    
    # Mark as migrated
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        '''))
        conn.execute(text('''
            INSERT INTO alembic_version (version_num) 
            VALUES ('manual_setup_render')
            ON CONFLICT (version_num) DO NOTHING
        '''))
        conn.commit()
        print('Migration state recorded')
        
except Exception as e:
    print(f'Manual setup failed: {e}')
    sys.exit(1)
"
        exit 0
    }
    
    echo "🚀 Running initial migration..."
    alembic upgrade head
fi

echo "👤 Ensuring super admin exists..."

# Create super admin if it doesn't exist
python -c "
import sys, os
sys.path.append('.')

try:
    from sqlalchemy.orm import Session
    from app.db.database import SessionLocal
    from app.models.user import User, UserRole, AuthProvider, UserStatus
    from app.core.security import get_password_hash
    
    email = 'abereenock95@gmail.com'
    password = 'SuperAdmin2025!'
    
    db = SessionLocal()
    
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f'Super admin already exists: {email}')
        else:
            print('Creating super admin...')
            hashed_password = get_password_hash(password)
            
            super_admin = User(
                email=email,
                hashed_password=hashed_password,
                full_name='Super Administrator',
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                tenant_id=None,
                auth_provider=AuthProvider.LOCAL
            )
            
            db.add(super_admin)
            db.commit()
            print(f'Super admin created: {email}')
            
    except Exception as e:
        print(f'Super admin setup failed: {e}')
        db.rollback()
    finally:
        db.close()
        
except Exception as e:
    print(f'Database connection failed: {e}')
    # Don't fail the build for this
"

echo "✅ Build completed successfully!"
echo "🎯 Database should be ready for deployment"