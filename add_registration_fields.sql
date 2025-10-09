-- Add missing columns to public_registrations table
ALTER TABLE public_registrations 
ADD COLUMN IF NOT EXISTS dietary_requirements TEXT,
ADD COLUMN IF NOT EXISTS accommodation_needs TEXT,
ADD COLUMN IF NOT EXISTS certificate_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS code_of_conduct_confirm VARCHAR(10),
ADD COLUMN IF NOT EXISTS travel_requirements_confirm VARCHAR(10);