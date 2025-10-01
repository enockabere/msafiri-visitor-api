#!/bin/bash

echo "🔄 Resetting database and migrations..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Backup current .env if it exists
if [ -f .env ]; then
    echo "📋 Backing up .env file..."
    cp .env .env.backup
fi

# Run the safe reset script
python3 safe_reset.py

# Create a super admin user
echo "👤 Creating super admin user..."
python3 create_admin.py

echo "✅ Database reset complete!"
echo "🔑 Login credentials: admin@msafiri.com / admin123"