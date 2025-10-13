-- Add missing columns to vendor_accommodations table
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS latitude VARCHAR(20);
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS longitude VARCHAR(20);
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS single_rooms INTEGER DEFAULT 0;
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS double_rooms INTEGER DEFAULT 0;