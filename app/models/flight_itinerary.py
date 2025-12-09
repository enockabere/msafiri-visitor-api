from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class FlightItinerary(BaseModel):
    __tablename__ = "flight_itineraries"

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_email = Column(String(255), nullable=False)

    # Flight location details
    departure_city = Column(String(255), nullable=True)
    arrival_city = Column(String(255), nullable=True)
    departure_airport = Column(String(100), nullable=True)
    arrival_airport = Column(String(100), nullable=True)
    pickup_location = Column(String(255), nullable=True)

    # Flight timing
    departure_date = Column(DateTime, nullable=True)
    departure_time = Column(String(50), nullable=True)
    arrival_date = Column(DateTime, nullable=True)
    arrival_time = Column(String(50), nullable=True)

    # Flight details
    flight_number = Column(String(100), nullable=True)
    airline = Column(String(255), nullable=True)
    booking_reference = Column(String(100), nullable=True)
    ticket_number = Column(String(100), nullable=True)
    cabin_class = Column(String(50), nullable=True)
    seat_number = Column(String(20), nullable=True)
    baggage_allowance = Column(String(100), nullable=True)
    special_requests = Column(Text, nullable=True)

    # Itinerary type (arrival or departure)
    itinerary_type = Column(String(50), nullable=True)

    # Status and confirmation
    status = Column(String(50), nullable=True)
    confirmation_date = Column(DateTime, nullable=True)

    # Attachments and notes
    ticket_attachment = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    # Destination field
    destination = Column(String(255), nullable=True)

    # Relationships
    event = relationship("Event")