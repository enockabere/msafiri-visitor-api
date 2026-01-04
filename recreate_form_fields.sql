-- Fix the field_options column type and data
-- First, drop the existing table and recreate with correct structure
DROP TABLE IF EXISTS form_fields CASCADE;

-- Recreate the table with TEXT column for field_options (not array)
CREATE TABLE form_fields (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_label VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL DEFAULT 'text',
    field_options TEXT, -- JSON string, not array
    is_required BOOLEAN NOT NULL DEFAULT false,
    order_index INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_protected BOOLEAN NOT NULL DEFAULT false,
    section VARCHAR(50) DEFAULT 'personal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_form_fields_event_id ON form_fields(event_id);
CREATE INDEX idx_form_fields_order ON form_fields(event_id, order_index);
CREATE INDEX idx_form_fields_active ON form_fields(event_id, is_active);
CREATE UNIQUE INDEX idx_form_fields_unique_name ON form_fields(event_id, field_name) WHERE is_active = true;

-- Insert basic form fields with proper JSON strings
INSERT INTO form_fields (event_id, field_name, field_label, field_type, is_required, order_index, is_protected, section) VALUES
(7, 'firstName', 'First Name', 'text', true, 101, true, 'personal'),
(7, 'lastName', 'Last Name', 'text', true, 102, true, 'personal'),
(7, 'personalEmail', 'Personal Email', 'email', true, 201, true, 'contact'),
(7, 'phoneNumber', 'Phone Number', 'text', true, 206, true, 'contact');

INSERT INTO form_fields (event_id, field_name, field_label, field_type, field_options, is_required, order_index, is_protected, section) VALUES
(7, 'oc', 'Operational Center (OC)', 'select', '["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]', true, 103, true, 'personal'),
(7, 'contractStatus', 'Contract Status', 'select', '["National Staff", "International Staff", "Consultant", "Volunteer"]', true, 104, true, 'personal'),
(7, 'genderIdentity', 'Gender Identity', 'select', '["Male", "Female", "Non-binary", "Prefer not to say"]', true, 106, true, 'personal'),
(7, 'travellingInternationally', 'Are you travelling internationally?', 'select', '["Yes", "No"]', true, 301, true, 'travel'),
(7, 'accommodationType', 'Accommodation Type', 'select', '["Staying at venue", "Travelling daily"]', true, 303, true, 'travel'),
(7, 'codeOfConductConfirm', 'I confirm that I have read and agree to abide by the MSF Code of Conduct', 'checkbox', '["I agree"]', true, 404, true, 'final');

COMMIT;