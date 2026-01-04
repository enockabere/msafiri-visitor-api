-- Direct SQL script to create vetting committee tables
-- Run this directly on the database to avoid migration cycle issues

-- Create enums first
DO $$ BEGIN
    CREATE TYPE vettingstatus AS ENUM ('open', 'pending_approval', 'approved');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE approvalstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CHANGES_REQUESTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add user roles if they don't exist
DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE 'VETTING_COMMITTEE';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TYPE userrole ADD VALUE 'VETTING_APPROVER';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create vetting_committees table
CREATE TABLE IF NOT EXISTS vetting_committees (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    selection_start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    selection_end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status vettingstatus DEFAULT 'open',
    approver_email VARCHAR(255) NOT NULL,
    approver_id INTEGER REFERENCES users(id),
    submitted_at TIMESTAMP WITH TIME ZONE,
    submitted_by VARCHAR(255),
    approval_status approvalstatus DEFAULT 'PENDING',
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by VARCHAR(255),
    approval_notes TEXT,
    created_by VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,  -- STRING, not INTEGER
    email_notifications_enabled BOOLEAN DEFAULT FALSE,
    selected_template_id INTEGER,
    not_selected_template_id INTEGER,
    reminders_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_vetting_committees_event_id ON vetting_committees(event_id);
CREATE INDEX IF NOT EXISTS idx_vetting_committees_tenant_id ON vetting_committees(tenant_id);

-- Create vetting_committee_members table
CREATE TABLE IF NOT EXISTS vetting_committee_members (
    id SERIAL PRIMARY KEY,
    committee_id INTEGER NOT NULL REFERENCES vetting_committees(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    invitation_sent BOOLEAN DEFAULT FALSE,
    invitation_sent_at TIMESTAMP WITH TIME ZONE,
    invitation_token VARCHAR(255),
    first_login TIMESTAMP WITH TIME ZONE,
    last_activity TIMESTAMP WITH TIME ZONE,
    had_previous_role VARCHAR(50),
    role_removed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_vetting_committee_members_committee_id ON vetting_committee_members(committee_id);
CREATE INDEX IF NOT EXISTS idx_vetting_committee_members_email ON vetting_committee_members(email);

-- Create participant_selections table
CREATE TABLE IF NOT EXISTS participant_selections (
    id SERIAL PRIMARY KEY,
    committee_id INTEGER NOT NULL REFERENCES vetting_committees(id) ON DELETE CASCADE,
    participant_id INTEGER NOT NULL REFERENCES event_participants(id) ON DELETE CASCADE,
    selected BOOLEAN NOT NULL,
    selection_notes TEXT,
    selected_by VARCHAR(255) NOT NULL,
    selected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    approver_override BOOLEAN DEFAULT FALSE,
    override_notes TEXT,
    override_by VARCHAR(255),
    override_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(committee_id, participant_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_participant_selections_committee_id ON participant_selections(committee_id);
CREATE INDEX IF NOT EXISTS idx_participant_selections_participant_id ON participant_selections(participant_id);

-- Grant permissions to the application user (adjust username as needed)
GRANT ALL PRIVILEGES ON vetting_committees TO msafiri_user;
GRANT ALL PRIVILEGES ON vetting_committee_members TO msafiri_user;
GRANT ALL PRIVILEGES ON participant_selections TO msafiri_user;
GRANT USAGE, SELECT ON SEQUENCE vetting_committees_id_seq TO msafiri_user;
GRANT USAGE, SELECT ON SEQUENCE vetting_committee_members_id_seq TO msafiri_user;
GRANT USAGE, SELECT ON SEQUENCE participant_selections_id_seq TO msafiri_user;

-- Verify tables were created
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name IN ('vetting_committees', 'vetting_committee_members', 'participant_selections')
ORDER BY table_name, ordinal_position;