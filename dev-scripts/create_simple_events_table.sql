-- Drop events table if it exists
DROP TABLE IF EXISTS events;

-- Create simple events table
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    location VARCHAR(255) NOT NULL,
    tenant_id VARCHAR NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX ix_events_id ON events(id);
CREATE INDEX ix_events_tenant_id ON events(tenant_id);

-- Insert sample data
INSERT INTO events (title, description, start_date, end_date, location, tenant_id, created_by) VALUES
('Sample Event 1', 'This is a sample event for testing', '2024-02-01', '2024-02-03', 'Nairobi, Kenya', 'ko-oca', 'admin@example.com'),
('Sample Event 2', 'Another sample event', '2024-03-15', '2024-03-17', 'Mombasa, Kenya', 'ko-oca', 'admin@example.com');