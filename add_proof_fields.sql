-- Add proof of accommodation fields to event_participants table
ALTER TABLE event_participants 
ADD COLUMN IF NOT EXISTS proof_of_accommodation_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS proof_generated_at TIMESTAMP;

-- Add comment for documentation
COMMENT ON COLUMN event_participants.proof_of_accommodation_url IS 'URL to the generated proof of accommodation PDF document';
COMMENT ON COLUMN event_participants.proof_generated_at IS 'Timestamp when the proof of accommodation was generated';