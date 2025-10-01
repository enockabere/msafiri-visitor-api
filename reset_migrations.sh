#!/bin/bash

echo "🔄 Resetting database and migrations..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Backup current .env if it exists
if [ -f .env ]; then
    echo "📋 Backing up .env file..."
    cp .env .env.backup
fi

# Run the reset script
python3 reset_database.py

# Create a super admin user
echo "👤 Creating super admin user..."
python3 -c "
from app.core.database import get_db
from app.models.user import User, UserRole, UserStatus, AuthProvider
from app.core.security import get_password_hash
from sqlalchemy.orm import Session
import os

# Get database session
db = next(get_db())

# Check if super admin exists
existing_admin = db.query(User).filter(User.email == 'admin@msafiri.com').first()

if not existing_admin:
    # Create super admin
    admin_user = User(
        email='admin@msafiri.com',
        hashed_password=get_password_hash('admin123'),
        full_name='Super Administrator',
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        auth_provider=AuthProvider.LOCAL,
        tenant_id='default'
    )
    
    db.add(admin_user)
    db.commit()
    print('✅ Super admin created: admin@msafiri.com / admin123')
else:
    print('ℹ️  Super admin already exists')

db.close()
"

echo "✅ Database reset complete!"
echo "🔑 Login credentials: admin@msafiri.com / admin123"