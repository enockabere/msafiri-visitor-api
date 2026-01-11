-- Direct SQL to create user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    preferences JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_user_preferences_id ON user_preferences(id);
CREATE INDEX IF NOT EXISTS ix_user_preferences_user_id ON user_preferences(user_id);

-- Insert migration record to mark it as applied
INSERT INTO alembic_version (version_num) VALUES ('add_user_preferences') 
ON CONFLICT (version_num) DO NOTHING;