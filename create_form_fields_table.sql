-- Create form_fields table for dynamic form builder
CREATE TABLE IF NOT EXISTS form_fields (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_label VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL DEFAULT 'text',
    field_options TEXT[], -- Array of options for select/radio/checkbox fields
    is_required BOOLEAN NOT NULL DEFAULT false,
    order_index INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_protected BOOLEAN NOT NULL DEFAULT false, -- Protected fields cannot be deleted
    section VARCHAR(50) DEFAULT 'personal', -- personal, contact, travel, final
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_form_fields_event_id ON form_fields(event_id);
CREATE INDEX IF NOT EXISTS idx_form_fields_order ON form_fields(event_id, order_index);
CREATE INDEX IF NOT EXISTS idx_form_fields_active ON form_fields(event_id, is_active);

-- Create unique constraint to prevent duplicate field names per event
CREATE UNIQUE INDEX IF NOT EXISTS idx_form_fields_unique_name 
ON form_fields(event_id, field_name) WHERE is_active = true;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_form_fields_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_form_fields_updated_at
    BEFORE UPDATE ON form_fields
    FOR EACH ROW
    EXECUTE FUNCTION update_form_fields_updated_at();

-- Insert default form fields for existing events (optional)
-- This will create basic form structure for events that don't have form fields yet
INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT 
    e.id as event_id,
    'firstName' as field_name,
    'First Name' as field_label,
    'text' as field_type,
    true as is_required,
    101 as order_index,
    true as is_protected,
    'personal' as section
FROM events e
WHERE NOT EXISTS (
    SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'firstName'
);

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT 
    e.id as event_id,
    'lastName' as field_name,
    'Last Name' as field_label,
    'text' as field_type,
    true as is_required,
    102 as order_index,
    true as is_protected,
    'personal' as section
FROM events e
WHERE NOT EXISTS (
    SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'lastName'
);

INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section)
SELECT 
    e.id as event_id,
    'personalEmail' as field_name,
    'Personal Email' as field_label,
    'email' as field_type,
    true as is_required,
    201 as order_index,
    true as is_protected,
    'contact' as section
FROM events e
WHERE NOT EXISTS (
    SELECT 1 FROM form_fields ff WHERE ff.event_id = e.id AND ff.field_name = 'personalEmail'
);

COMMIT;