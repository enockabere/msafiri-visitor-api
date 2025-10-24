#!/usr/bin/env python3

import re

# Read the file
with open('d:/development/msafiri-visitor-api/app/api/v1/endpoints/events.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the booking check logic to exclude cancelled bookings
old_pattern = r'existing_booking = db\.query\(AccommodationAllocation\)\.filter\(\s*AccommodationAllocation\.participant_id == participation\.id\s*\)\.first\(\)'
new_pattern = '''existing_booking = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participation.id,
            AccommodationAllocation.status.in_(['booked', 'checked_in'])
        ).first()'''

# Replace all occurrences
content = re.sub(old_pattern, new_pattern, content)

# Write back to file
with open('d:/development/msafiri-visitor-api/app/api/v1/endpoints/events.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed booking check logic to exclude cancelled bookings")