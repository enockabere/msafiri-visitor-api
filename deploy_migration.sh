#!/bin/bash

# Script to run database migrations on the server
# Run this on the server where the API is deployed

echo "🔄 Running database migrations..."

# Navigate to the API directory
cd /path/to/msafiri-visitor-api

# Activate virtual environment if needed
# source venv/bin/activate

# Run Alembic migrations
alembic upgrade head

echo "✅ Database migrations completed!"

# Restart the API service
echo "🔄 Restarting API service..."
sudo systemctl restart gunicorn

echo "✅ API service restarted!"

echo "🎉 Migration deployment complete!"