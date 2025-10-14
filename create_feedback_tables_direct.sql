-- Direct SQL to create feedback tables
CREATE TABLE IF NOT EXISTS agenda_feedback (
    id SERIAL PRIMARY KEY,
    agenda_id INTEGER NOT NULL,
    user_email VARCHAR NOT NULL,
    rating FLOAT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agenda_id) REFERENCES event_agenda(id)
);

CREATE TABLE IF NOT EXISTS feedback_responses (
    id SERIAL PRIMARY KEY,
    feedback_id INTEGER NOT NULL,
    responder_email VARCHAR NOT NULL,
    response_text TEXT NOT NULL,
    is_like BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feedback_id) REFERENCES agenda_feedback(id)
);

CREATE INDEX IF NOT EXISTS ix_agenda_feedback_agenda_id ON agenda_feedback(agenda_id);
CREATE INDEX IF NOT EXISTS ix_agenda_feedback_user_email ON agenda_feedback(user_email);
CREATE INDEX IF NOT EXISTS ix_feedback_responses_feedback_id ON feedback_responses(feedback_id);