-- Add missing columns to events table in production
ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(100);
ALTER TABLE events ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Draft';
ALTER TABLE events ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE events ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE events ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,8);
ALTER TABLE events ADD COLUMN IF NOT EXISTS longitude NUMERIC(11,8);
ALTER TABLE events ADD COLUMN IF NOT EXISTS banner_image VARCHAR(500);
ALTER TABLE events ADD COLUMN IF NOT EXISTS agenda_document_url VARCHAR(500);
ALTER TABLE events ADD COLUMN IF NOT EXISTS registration_deadline DATE;
ALTER TABLE events ADD COLUMN IF NOT EXISTS vendor_accommodation_id INTEGER;

-- Add missing columns to event_participants table
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS position VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS project VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS gender VARCHAR(50);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS eta VARCHAR(255);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS requires_eta BOOLEAN DEFAULT FALSE;
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS passport_document VARCHAR(500);
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS ticket_document VARCHAR(500);

-- Add missing columns to vendor_accommodations table
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS latitude VARCHAR(20);
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS longitude VARCHAR(20);
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS single_rooms INTEGER DEFAULT 0;
ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS double_rooms INTEGER DEFAULT 0;