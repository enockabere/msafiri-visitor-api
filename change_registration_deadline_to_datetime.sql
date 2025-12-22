-- Migration: Change registration_deadline from DATE to TIMESTAMP
-- This allows storing both date and time for registration deadlines

-- Step 1: Alter the column type from DATE to TIMESTAMP
-- PostgreSQL will automatically convert existing date values to timestamp at 00:00:00
ALTER TABLE events
ALTER COLUMN registration_deadline TYPE TIMESTAMP WITHOUT TIME ZONE
USING registration_deadline::TIMESTAMP;

-- Verification query (run this after the migration)
-- SELECT id, title, registration_deadline FROM events LIMIT 5;
