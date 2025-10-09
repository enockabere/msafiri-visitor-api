-- Add missing columns to event_participants table
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS registration_type VARCHAR(50) DEFAULT 'self';
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS notes TEXT;

-- Check if column exists before renaming
DO $$
BEGIN
    IF EXISTS(SELECT * FROM information_schema.columns WHERE table_name='event_participants' AND column_name='invited_by') THEN
        ALTER TABLE event_participants RENAME COLUMN invited_by TO registered_by;
    END IF;
END $$;

-- Add registered_by column if it doesn't exist
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS registered_by VARCHAR(255);