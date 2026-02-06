from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Time
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class AirportPickup(BaseModel):
    __tablename__ = "airport_pickups"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, unique=True)
    driver_name = Column(String(255), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    driver_email = Column(String(255))
    vehicle_details = Column(String(255))
    pickup_time = Column(DateTime, nullable=False)
    destination = Column(String(500), nullable=False)
    special_instructions = Column(Text)
    travel_agent_email = Column(String(255))  # Agent who can access this pickup
    
    # Status tracking
    driver_confirmed = Column(Boolean, default=False)
    visitor_confirmed = Column(Boolean, default=False)
    admin_confirmed = Column(Boolean, default=False)
    welcome_package_confirmed = Column(Boolean, default=False)
    pickup_completed = Column(Boolean, default=False)
    
    # Confirmation details
    driver_confirmation_time = Column(DateTime)
    visitor_confirmation_time = Column(DateTime)
    admin_confirmation_time = Column(DateTime)
    confirmed_by_admin = Column(String(255))
    
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="airport_pickup")
