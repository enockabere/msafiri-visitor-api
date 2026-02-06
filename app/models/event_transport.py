from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RideStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EventRide(BaseModel):
    __tablename__ = "event_rides"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    departure_location = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    driver_name = Column(String(255), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    vehicle_details = Column(String(255))
    max_capacity = Column(Integer, nullable=False, default=4)
    current_occupancy = Column(Integer, nullable=False, default=0)
    status = Column(Enum(RideStatus), default=RideStatus.PENDING)
    special_instructions = Column(Text)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")
    ride_assignments = relationship("RideAssignment", back_populates="ride")

class RideAssignment(BaseModel):
    __tablename__ = "ride_assignments"
    
    ride_id = Column(Integer, ForeignKey("event_rides.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    pickup_location = Column(String(255))
    pickup_time = Column(DateTime)
    confirmed = Column(Boolean, default=False)
    boarded = Column(Boolean, default=False)
    assigned_by = Column(String(255), nullable=False)
    
    # Relationships
    ride = relationship("EventRide", back_populates="ride_assignments")
    participant = relationship("EventParticipant", back_populates="ride_assignments")

class RideRequest(BaseModel):
    __tablename__ = "ride_requests"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    pickup_location = Column(String(255), nullable=False)
    preferred_time = Column(DateTime, nullable=False)
    special_requirements = Column(Text)
    status = Column(String(20), default="pending")  # pending, approved, assigned, rejected
    admin_notes = Column(Text)
    approved_by = Column(String(255))
    
    # Relationships
    participant = relationship("EventParticipant")
    event = relationship("Event")
