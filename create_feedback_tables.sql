-- Create feedback tables
CREATE TABLE IF NOT EXISTS agenda_feedback (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL REFERENCES event_agenda(id),
    user_email VARCHAR NOT NULL,
    rating FLOAT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_agenda_feedback_id ON agenda_feedback(id);
CREATE INDEX IF NOT EXISTS ix_agenda_feedback_agenda_id ON agenda_feedback(agenda_id);
CREATE INDEX IF NOT EXISTS ix_agenda_feedback_user_email ON agenda_feedback(user_email);

CREATE TABLE IF NOT EXISTS feedback_responses (
    id SERIAL PRIMARY KEY,
    feedback_id INTEGER NOT NULL REFERENCES agenda_feedback(id),
    responder_email VARCHAR NOT NULL,
    response_text TEXT NOT NULL,
    is_like BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_feedback_responses_id ON feedback_responses(id);
CREATE INDEX IF NOT EXISTS ix_feedback_responses_feedback_id ON feedback_responses(feedback_id);