-- Create badge_templates table
CREATE TABLE IF NOT EXISTS badge_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_content TEXT,
    logo_url VARCHAR(500),
    logo_public_id VARCHAR(255),
    background_url VARCHAR(500),
    background_public_id VARCHAR(255),
    enable_qr_code BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    badge_size VARCHAR(50) DEFAULT 'standard',
    orientation VARCHAR(20) DEFAULT 'portrait',
    contact_phone VARCHAR(255),
    website_url VARCHAR(500),
    avatar_url VARCHAR(500),
    include_avatar BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_badge_templates_id ON badge_templates (id);
CREATE INDEX IF NOT EXISTS ix_badge_templates_name ON badge_templates (name);