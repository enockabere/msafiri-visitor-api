# File: app/models/event.py
from sqlalchemy import Column, String, Text, Boolean, Numeric, ForeignKey, Date, Integer, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Event(BaseModel):
    __tablename__ = "events"
    
    title = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    event_type = Column(String(100))
    status = Column(String(50), default='Draft')
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Location & Logistics
    location = Column(String(255))
    address = Column(Text)
    country = Column(String(100))
    latitude = Column(Numeric(10,8))
    longitude = Column(Numeric(11,8))
    
    # Media
    banner_image = Column(String(500))
    agenda_document_url = Column(String(500))
    
    # Legacy fields
    duration_days = Column(Integer)
    perdiem_rate = Column(Numeric(10,2))
    
    # Registration
    registration_deadline = Column(Date)
    
    # Venue
    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id"), nullable=True)
    
    # Accommodation Planning
    expected_participants = Column(Integer)
    single_rooms = Column(Integer)
    double_rooms = Column(Integer)
    
    # Metadata
    tenant_id = Column(Integer, nullable=False)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    attachments = relationship("EventAttachment", back_populates="event", cascade="all, delete-orphan")
    venue = relationship("VendorAccommodation", foreign_keys=[vendor_accommodation_id])
    passport_records = relationship("PassportRecord", back_populates="event", cascade="all, delete-orphan")