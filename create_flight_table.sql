-- Create flight_itineraries table if it doesn't exist
CREATE TABLE IF NOT EXISTS flight_itineraries (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_id INTEGER NOT NULL REFERENCES events(id),
    user_email VARCHAR(255) NOT NULL,
    airline VARCHAR(100),
    flight_number VARCHAR(50),
    departure_airport VARCHAR(100) NOT NULL,
    arrival_airport VARCHAR(100) NOT NULL,
    departure_date TIMESTAMP NOT NULL,
    arrival_date TIMESTAMP NOT NULL,
    itinerary_type VARCHAR(50) NOT NULL,
    confirmed BOOLEAN DEFAULT FALSE,
    ticket_record_id INTEGER
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_flight_itineraries_user_email ON flight_itineraries(user_email);
CREATE INDEX IF NOT EXISTS idx_flight_itineraries_event_id ON flight_itineraries(event_id);