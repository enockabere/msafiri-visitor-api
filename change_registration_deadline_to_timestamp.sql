-- Change registration_deadline from DATE to TIMESTAMP WITH TIME ZONE

-- First, add a new temporary column
ALTER TABLE events ADD COLUMN registration_deadline_temp TIMESTAMP WITH TIME ZONE;

-- Copy data from old column to new column, setting time to 09:00:00
UPDATE events 
SET registration_deadline_temp = registration_deadline + INTERVAL '9 hours'
WHERE registration_deadline IS NOT NULL;

-- Drop the old column
ALTER TABLE events DROP COLUMN registration_deadline;

-- Rename the new column
ALTER TABLE events RENAME COLUMN registration_deadline_temp TO registration_deadline;