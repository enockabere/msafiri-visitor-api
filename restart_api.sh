#!/bin/bash

# Restart MSafiri API Service
echo "🔄 Restarting MSafiri API service..."

# Stop the service
sudo systemctl stop msafiri-api
echo "⏹️  Service stopped"

# Start the service
sudo systemctl start msafiri-api
echo "▶️  Service started"

# Check status
sudo systemctl status msafiri-api --no-pager -l
echo "✅ Service restart completed"

# Show recent logs
echo "📋 Recent logs:"
sudo journalctl -u msafiri-api -n 10 --no-pager