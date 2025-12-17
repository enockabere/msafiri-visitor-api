-- Create line_manager_recommendations table
CREATE TABLE IF NOT EXISTS line_manager_recommendations (
    id SERIAL PRIMARY KEY,
    participant_email VARCHAR(255) NOT NULL,
    event_id INTEGER NOT NULL,
    line_manager_email VARCHAR(255) NOT NULL,
    is_recommended BOOLEAN DEFAULT NULL,
    recommendation_text TEXT,
    submitted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_participant_event 
ON line_manager_recommendations(participant_email, event_id);