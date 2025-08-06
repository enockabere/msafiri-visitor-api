#!/usr/bin/env bash

set -o errexit  # Exit on error

echo "🔄 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📋 Running database migrations..."
alembic upgrade head

echo "✅ Build completed successfully!"