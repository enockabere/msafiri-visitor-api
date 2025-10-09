-- Remove attachments column from events table
ALTER TABLE events DROP COLUMN IF EXISTS attachments;