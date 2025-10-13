-- Add vendor_accommodation_id column to events table
ALTER TABLE events ADD COLUMN IF NOT EXISTS vendor_accommodation_id INTEGER;