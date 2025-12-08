-- Comprehensive script to create all missing tables
-- Run this to ensure database has all required tables

-- 0. Ensure voucher_scanner role exists
INSERT INTO roles (name, description, created_at, updated_at)
VALUES ('voucher_scanner', 'Can scan and redeem vouchers at events', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- 1. Create event_voucher_scanners table
CREATE TABLE IF NOT EXISTS event_voucher_scanners (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    tenant_id INTEGER NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_event_voucher_scanners_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_voucher_scanners_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_event_scanner UNIQUE (user_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_event_id ON event_voucher_scanners(event_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_user_id ON event_voucher_scanners(user_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_tenant_id ON event_voucher_scanners(tenant_id);
CREATE INDEX IF NOT EXISTS idx_event_voucher_scanners_active ON event_voucher_scanners(is_active);

-- 2. Create public_registrations table
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

CREATE INDEX IF NOT EXISTS idx_public_registrations_event_id ON public_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_participant_id ON public_registrations(participant_id);
CREATE INDEX IF NOT EXISTS idx_public_registrations_personal_email ON public_registrations(personal_email);

-- 3. Create travel_checklist_progress table if it doesn't exist
CREATE TABLE IF NOT EXISTS travel_checklist_progress (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    checklist_items JSONB,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, user_email)
);

CREATE INDEX IF NOT EXISTS idx_travel_checklist_progress_event_id ON travel_checklist_progress(event_id);
CREATE INDEX IF NOT EXISTS idx_travel_checklist_progress_user_email ON travel_checklist_progress(user_email);

-- 4. Create itinerary_reminders table if it doesn't exist
CREATE TABLE IF NOT EXISTS itinerary_reminders (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    reminder_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_itinerary_reminders_id ON itinerary_reminders(id);
CREATE INDEX IF NOT EXISTS idx_itinerary_reminders_event_id ON itinerary_reminders(event_id);
CREATE INDEX IF NOT EXISTS idx_itinerary_reminders_user_email ON itinerary_reminders(user_email);

-- Show created tables
SELECT 'event_voucher_scanners' as table_name, COUNT(*) as row_count FROM event_voucher_scanners
UNION ALL
SELECT 'public_registrations', COUNT(*) FROM public_registrations
UNION ALL
SELECT 'travel_checklist_progress', COUNT(*) FROM travel_checklist_progress
UNION ALL
SELECT 'itinerary_reminders', COUNT(*) FROM itinerary_reminders;
