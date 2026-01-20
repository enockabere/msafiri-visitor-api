-- Fix missing vendor event accommodation setup for event 18

-- First, check the current event details
SELECT 
    id, title, vendor_accommodation_id, single_rooms, double_rooms, tenant_id
FROM events 
WHERE id = 18;

-- Check if vendor event setup already exists
SELECT * FROM vendor_event_accommodations 
WHERE event_id = 18;

-- Create the vendor event accommodation setup
INSERT INTO vendor_event_accommodations (
    tenant_id,
    vendor_accommodation_id,
    event_id,
    event_name,
    single_rooms,
    double_rooms,
    total_capacity,
    current_occupants,
    is_active,
    created_by,
    created_at
)
SELECT 
    e.tenant_id,
    e.vendor_accommodation_id,
    e.id,
    e.title,
    e.single_rooms,
    e.double_rooms,
    (e.single_rooms + (e.double_rooms * 2)) as total_capacity,
    0 as current_occupants,
    true as is_active,
    'fix_script' as created_by,
    NOW() as created_at
FROM events e
WHERE e.id = 18
  AND e.vendor_accommodation_id IS NOT NULL
  AND e.single_rooms IS NOT NULL
  AND e.double_rooms IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM vendor_event_accommodations 
    WHERE event_id = 18
  );

-- Verify the creation
SELECT * FROM vendor_event_accommodations 
WHERE event_id = 18;