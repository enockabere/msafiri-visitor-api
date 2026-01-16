-- Fix notification priority column type
-- Run this on your production database

-- Drop the enum constraint if it exists
ALTER TABLE notifications ALTER COLUMN priority DROP DEFAULT;
ALTER TABLE notifications ALTER COLUMN priority TYPE VARCHAR(20);
ALTER TABLE notifications ALTER COLUMN priority SET DEFAULT 'MEDIUM';

-- Update any NULL values to MEDIUM
UPDATE notifications SET priority = 'MEDIUM' WHERE priority IS NULL;

-- Ensure all values are uppercase
UPDATE notifications SET priority = UPPER(priority) WHERE priority IS NOT NULL;
