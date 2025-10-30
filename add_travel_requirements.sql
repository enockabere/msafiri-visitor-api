-- Add travel requirements for testing
-- Run this in your PostgreSQL database

-- First, check if the requirement already exists
SELECT * FROM country_travel_requirements WHERE tenant_id = 1 AND country = 'Kenya';

-- If it doesn't exist, insert a new one
INSERT INTO country_travel_requirements (
    tenant_id, 
    country, 
    visa_required, 
    eta_required, 
    passport_required, 
    flight_ticket_required, 
    additional_requirements, 
    created_by, 
    created_at
) VALUES (
    1,  -- Adjust tenant_id as needed
    'Kenya',
    true,
    false,
    true,
    true,
    '[
        {
            "name": "Visa Required",
            "required": true,
            "description": "Valid visa document for entry"
        },
        {
            "name": "Accommodation Booking",
            "required": true,
            "description": "Hotel or accommodation confirmation"
        },
        {
            "name": "Travel Insurance",
            "required": true,
            "description": "Valid travel insurance coverage"
        }
    ]'::json,
    'admin@test.com',
    NOW()
) ON CONFLICT (tenant_id, country) DO UPDATE SET
    additional_requirements = '[
        {
            "name": "Visa Required",
            "required": true,
            "description": "Valid visa document for entry"
        },
        {
            "name": "Accommodation Booking",
            "required": true,
            "description": "Hotel or accommodation confirmation"
        },
        {
            "name": "Travel Insurance",
            "required": true,
            "description": "Valid travel insurance coverage"
        }
    ]'::json,
    updated_by = 'admin@test.com',
    updated_at = NOW();

-- Verify the insertion
SELECT * FROM country_travel_requirements WHERE tenant_id = 1 AND country = 'Kenya';