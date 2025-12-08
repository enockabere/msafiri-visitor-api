-- Create public_registrations table if it doesn't exist
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_public_registrations_event_id ON public_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_participant_id ON public_registrations(participant_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_personal_email ON public_registrations(personal_email);
