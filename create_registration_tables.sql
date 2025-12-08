-- ========================================
-- Create Public Registrations Tables
-- Run this on the server to fix missing tables
-- ========================================

-- 1. Create public_registrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS public_registrations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    participant_id INTEGER REFERENCES event_participants(id) ON DELETE CASCADE,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    oc VARCHAR(50) NOT NULL,
    contract_status VARCHAR(100) NOT NULL,
    contract_type VARCHAR(50) NOT NULL,
    gender_identity VARCHAR(100) NOT NULL,
    sex VARCHAR(50) NOT NULL,
    pronouns VARCHAR(50) NOT NULL,
    current_position VARCHAR(255) NOT NULL,
    country_of_work VARCHAR(255),
    project_of_work VARCHAR(255),
    personal_email VARCHAR(255) NOT NULL,
    msf_email VARCHAR(255),
    hrco_email VARCHAR(255),
    career_manager_email VARCHAR(255),
    ld_manager_email VARCHAR(255),
    line_manager_email VARCHAR(255),
    phone_number VARCHAR(50) NOT NULL,
    travelling_internationally VARCHAR(10),
    travelling_from_country VARCHAR(255),
    accommodation_type VARCHAR(100),
    dietary_requirements TEXT,
    accommodation_needs TEXT,
    daily_meals TEXT,
    certificate_name VARCHAR(255),
    badge_name VARCHAR(255),
    motivation_letter TEXT,
    code_of_conduct_confirm VARCHAR(10),
    travel_requirements_confirm VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add travelling_from_country column if it doesn't exist (for existing tables)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'public_registrations'
        AND column_name = 'travelling_from_country'
    ) THEN
        ALTER TABLE public_registrations ADD COLUMN travelling_from_country VARCHAR(255);
    END IF;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_public_registrations_event_id ON public_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_participant_id ON public_registrations(participant_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_personal_email ON public_registrations(personal_email);
CREATE INDEX IF NOT EXISTS idx_public_registrations_msf_email ON public_registrations(msf_email);

-- 2. Create line_manager_recommendations table if it doesn't exist
CREATE TABLE IF NOT EXISTS line_manager_recommendations (
    id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES public_registrations(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    participant_name VARCHAR(255) NOT NULL,
    participant_email VARCHAR(255) NOT NULL,
    line_manager_email VARCHAR(255) NOT NULL,
    operation_center VARCHAR(50),
    event_title VARCHAR(255),
    event_dates VARCHAR(255),
    event_location VARCHAR(255),
    recommendation_token VARCHAR(255) UNIQUE NOT NULL,
    recommendation_status VARCHAR(50) DEFAULT 'pending',
    recommendation_text TEXT,
    recommendation_decision VARCHAR(50),
    recommended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for line_manager_recommendations
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_registration_id ON line_manager_recommendations(registration_id);
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_event_id ON line_manager_recommendations(event_id);
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_token ON line_manager_recommendations(recommendation_token);
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_status ON line_manager_recommendations(recommendation_status);

-- Grant permissions (adjust as needed for your database user)
-- GRANT ALL PRIVILEGES ON TABLE public_registrations TO your_database_user;
-- GRANT ALL PRIVILEGES ON TABLE line_manager_recommendations TO your_database_user;
-- GRANT USAGE, SELECT ON SEQUENCE public_registrations_id_seq TO your_database_user;
-- GRANT USAGE, SELECT ON SEQUENCE line_manager_recommendations_id_seq TO your_database_user;

-- Verify tables were created
SELECT 'public_registrations table created/verified' as status
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'public_registrations');

SELECT 'line_manager_recommendations table created/verified' as status
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'line_manager_recommendations');

-- Show columns for verification
SELECT 'Columns in public_registrations:' as info;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'public_registrations'
ORDER BY ordinal_position;

SELECT 'Columns in line_manager_recommendations:' as info;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'line_manager_recommendations'
ORDER BY ordinal_position;
