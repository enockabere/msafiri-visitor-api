from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Text, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class TransportRequest(BaseModel):
    __tablename__ = "transport_requests"
    
    # Location details
    pickup_address = Column(String(500), nullable=False)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    
    dropoff_address = Column(String(500), nullable=False)
    dropoff_latitude = Column(Float, nullable=True)
    dropoff_longitude = Column(Float, nullable=True)
    
    # Timing
    pickup_time = Column(DateTime, nullable=False)
    
    # Passenger details
    passenger_name = Column(String(255), nullable=False)
    passenger_phone = Column(String(50), nullable=False)
    passenger_email = Column(String(255), nullable=True)
    
    # Vehicle and flight details
    vehicle_type = Column(String(100), nullable=True)
    flight_details = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # References
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    flight_itinerary_id = Column(Integer, ForeignKey("flight_itineraries.id"), nullable=True)
    user_email = Column(String(255), nullable=False)
    
    # Status
    status = Column(String(50), default="pending")  # pending, confirmed, completed, cancelled
    
    # Relationships
    event = relationship("Event")
    flight_itinerary = relationship("FlightItinerary")