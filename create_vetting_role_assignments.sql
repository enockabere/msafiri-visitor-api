-- Create vetting_role_assignments table
-- This fixes the error: relation "vetting_role_assignments" does not exist

CREATE TABLE IF NOT EXISTS vetting_role_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    committee_id INTEGER NOT NULL REFERENCES vetting_committees(id) ON DELETE CASCADE,
    role_type VARCHAR(50) NOT NULL,
    removed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vetting_role_assignments_user_id ON vetting_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_vetting_role_assignments_committee_id ON vetting_role_assignments(committee_id);

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON TABLE vetting_role_assignments TO msafiri_user;
GRANT USAGE, SELECT ON SEQUENCE vetting_role_assignments_id_seq TO msafiri_user;