#!/usr/bin/env python3

# Read the file
with open('d:/development/msafiri-visitor-api/app/api/v1/endpoints/events.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Event import after the existing imports
content = content.replace(
    'from app.models.guesthouse import AccommodationAllocation, VendorAccommodation',
    'from app.models.guesthouse import AccommodationAllocation, VendorAccommodation\n        from app.models.event import Event'
)

# Write back to file
with open('d:/development/msafiri-visitor-api/app/api/v1/endpoints/events.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added Event import to fix NameError")