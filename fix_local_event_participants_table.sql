-- Add missing columns to event_participants table in local database
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_role VARCHAR(100);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS position VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS project VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS gender VARCHAR(50);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS eta VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS requires_eta BOOLEAN DEFAULT FALSE;
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS passport_document VARCHAR(500);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS ticket_document VARCHAR(500);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS dietary_requirements TEXT;
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS accommodation_type VARCHAR(100);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_name VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_email VARCHAR(255);