-- Create form_responses table
CREATE TABLE IF NOT EXISTS form_responses (
    id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
    field_id INTEGER NOT NULL REFERENCES form_fields(id) ON DELETE CASCADE,
    field_value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_form_responses_registration_id ON form_responses(registration_id);
CREATE INDEX IF NOT EXISTS idx_form_responses_field_id ON form_responses(field_id);

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON TABLE form_responses TO msafiri_user;
GRANT USAGE, SELECT ON SEQUENCE form_responses_id_seq TO msafiri_user;

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_form_responses_updated_at 
    BEFORE UPDATE ON form_responses 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();