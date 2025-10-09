-- Fix transport booking enum constraints
-- Drop existing constraints if they exist
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_booking_type_check;
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_status_check;
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_vendor_type_check;

-- Add correct enum constraints with lowercase values
ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_booking_type_check 
    CHECK (booking_type IN ('airport_pickup', 'event_transfer', 'office_visit', 'custom'));

ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_status_check 
    CHECK (status IN ('pending', 'confirmed', 'package_collected', 'visitor_picked_up', 'in_transit', 'completed', 'cancelled'));

ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_vendor_type_check 
    CHECK (vendor_type IN ('absolute_taxi', 'manual_vendor'));

-- Fix transport_status_updates table if it exists
ALTER TABLE transport_status_updates DROP CONSTRAINT IF EXISTS transport_status_updates_status_check;
ALTER TABLE transport_status_updates ADD CONSTRAINT transport_status_updates_status_check 
    CHECK (status IN ('pending', 'confirmed', 'package_collected', 'visitor_picked_up', 'in_transit', 'completed', 'cancelled'));

-- Fix transport_vendors table if it exists  
ALTER TABLE transport_vendors DROP CONSTRAINT IF EXISTS transport_vendors_vendor_type_check;
ALTER TABLE transport_vendors ADD CONSTRAINT transport_vendors_vendor_type_check 
    CHECK (vendor_type IN ('absolute_taxi', 'manual_vendor'));