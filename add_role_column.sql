-- Add role column to event_participants table
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'attendee';

-- Update existing records to have default role
UPDATE event_participants SET role = 'attendee' WHERE role IS NULL;