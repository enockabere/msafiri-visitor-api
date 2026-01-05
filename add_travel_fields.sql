-- Add missing travel preference fields to event_participants table
-- Run this SQL script directly on the database

ALTER TABLE event_participants 
ADD COLUMN IF NOT EXISTS accommodation_preference VARCHAR(100),
ADD COLUMN IF NOT EXISTS has_dietary_requirements BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS has_accommodation_needs BOOLEAN DEFAULT FALSE;

-- Update existing records to have default values
UPDATE event_participants 
SET has_dietary_requirements = FALSE 
WHERE has_dietary_requirements IS NULL;

UPDATE event_participants 
SET has_accommodation_needs = FALSE 
WHERE has_accommodation_needs IS NULL;