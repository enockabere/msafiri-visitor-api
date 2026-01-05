#!/bin/bash

# Install WeasyPrint for PDF generation
echo "Installing WeasyPrint and dependencies..."

# Install system dependencies for WeasyPrint
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# Install WeasyPrint in the virtual environment
pip install weasyprint

echo "WeasyPrint installation completed!"
echo "Please restart the API service: sudo systemctl restart msafiri-api"