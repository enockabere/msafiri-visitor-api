-- ========================================
-- Update public_registrations table to match new registration form
-- Adds missing columns required by the current code
-- ========================================

-- Add event_id column (critical - links registration to event)
ALTER TABLE public_registrations
ADD COLUMN IF NOT EXISTS event_id INTEGER REFERENCES events(id) ON DELETE CASCADE;

-- Add work-related columns
ALTER TABLE public_registrations
ADD COLUMN IF NOT EXISTS oc VARCHAR(50),
ADD COLUMN IF NOT EXISTS contract_status VARCHAR(100),
ADD COLUMN IF NOT EXISTS contract_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS sex VARCHAR(50),
ADD COLUMN IF NOT EXISTS pronouns VARCHAR(50),
ADD COLUMN IF NOT EXISTS current_position VARCHAR(255),
ADD COLUMN IF NOT EXISTS country_of_work VARCHAR(255),
ADD COLUMN IF NOT EXISTS project_of_work VARCHAR(255);

-- Add email columns
ALTER TABLE public_registrations
ADD COLUMN IF NOT EXISTS msf_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS hrco_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS career_manager_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS ld_manager_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS line_manager_email VARCHAR(255);

-- Add other registration fields
ALTER TABLE public_registrations
ADD COLUMN IF NOT EXISTS badge_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS motivation_letter TEXT;

-- Create index on event_id for better query performance
CREATE INDEX IF NOT EXISTS idx_public_registrations_event_id ON public_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_msf_email ON public_registrations(msf_email);

-- Verify the columns were added
SELECT 'Columns added successfully!' as status;

-- Show all columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'public_registrations'
ORDER BY ordinal_position;
