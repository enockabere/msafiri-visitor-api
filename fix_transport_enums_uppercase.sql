-- Fix transport booking enum constraints to match SQLAlchemy enum names (uppercase)
-- Drop existing constraints if they exist
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_booking_type_check;
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_status_check;
ALTER TABLE transport_bookings DROP CONSTRAINT IF EXISTS transport_bookings_vendor_type_check;

-- Add correct enum constraints with uppercase enum names (what SQLAlchemy sends)
ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_booking_type_check 
    CHECK (booking_type IN ('AIRPORT_PICKUP', 'EVENT_TRANSFER', 'OFFICE_VISIT', 'CUSTOM'));

ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_status_check 
    CHECK (status IN ('PENDING', 'CONFIRMED', 'PACKAGE_COLLECTED', 'VISITOR_PICKED_UP', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED'));

ALTER TABLE transport_bookings ADD CONSTRAINT transport_bookings_vendor_type_check 
    CHECK (vendor_type IN ('ABSOLUTE_TAXI', 'MANUAL_VENDOR'));

-- Fix transport_status_updates table if it exists
ALTER TABLE transport_status_updates DROP CONSTRAINT IF EXISTS transport_status_updates_status_check;
ALTER TABLE transport_status_updates ADD CONSTRAINT transport_status_updates_status_check 
    CHECK (status IN ('PENDING', 'CONFIRMED', 'PACKAGE_COLLECTED', 'VISITOR_PICKED_UP', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED'));

-- Fix transport_vendors table if it exists  
ALTER TABLE transport_vendors DROP CONSTRAINT IF EXISTS transport_vendors_vendor_type_check;
ALTER TABLE transport_vendors ADD CONSTRAINT transport_vendors_vendor_type_check 
    CHECK (vendor_type IN ('ABSOLUTE_TAXI', 'MANUAL_VENDOR'));