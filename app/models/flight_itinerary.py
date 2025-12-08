from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class FlightItinerary(BaseModel):
    __tablename__ = "flight_itineraries"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_email = Column(String(255), nullable=False)
    
    # Flight details
    airline = Column(String(100), nullable=True)
    flight_number = Column(String(50), nullable=True)
    departure_city = Column(String(255), nullable=True)  # Database has departure_city
    arrival_city = Column(String(255), nullable=True)  # Database has arrival_city
    departure_date = Column(DateTime, nullable=True)
    arrival_date = Column(DateTime, nullable=True)
    
    # Departure-specific fields
    pickup_location = Column(String(255), nullable=True)  # For departure itineraries
    
    # Arrival-specific fields
    destination = Column(String(255), nullable=True)  # For arrival itineraries
    
    # Itinerary type
    itinerary_type = Column(String(50), nullable=False)  # 'arrival', 'departure', 'custom'
    
    # Status
    confirmed = Column(Boolean, default=False)
    pickup_confirmed = Column(Boolean, default=False, nullable=False)
    
    # Ticket data (if extracted from uploaded ticket)
    ticket_record_id = Column(Integer, nullable=True)  # External API record ID
    
    # Relationships
    event = relationship("Event")