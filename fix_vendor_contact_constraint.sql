-- Make contact fields nullable in vendor_accommodations table
ALTER TABLE vendor_accommodations ALTER COLUMN contact_person DROP NOT NULL;
ALTER TABLE vendor_accommodations ALTER COLUMN contact_phone DROP NOT NULL;
ALTER TABLE vendor_accommodations ALTER COLUMN contact_email DROP NOT NULL;