-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_days INTEGER NOT NULL,
    perdiem_rate NUMERIC(10,2),
    location VARCHAR(255),
    event_location VARCHAR(500) NOT NULL,
    accommodation_details TEXT,
    event_room_info TEXT,
    food_info TEXT,
    room_rate NUMERIC(10,2),
    other_facilities TEXT,
    tenant_id VARCHAR NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_events_id ON events(id);
CREATE INDEX IF NOT EXISTS ix_events_tenant_id ON events(tenant_id);

-- Add foreign key constraint if tenants table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN
        ALTER TABLE events ADD CONSTRAINT fk_events_tenant_id FOREIGN KEY (tenant_id) REFERENCES tenants(slug);
    END IF;
END $$;