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
    registration_deadline = Column(DateTime, nullable=False)
    
    # Venue
    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id"), nullable=True)
    
    # Templates
    invitation_template_id = Column(Integer, ForeignKey("invitation_templates.id"), nullable=True)
    
    # Accommodation Planning
    expected_participants = Column(Integer)
    accommodation_type = Column(String(50))  # FullBoard, HalfBoard, BedAndBreakfast, BedOnly
    single_rooms = Column(Integer)
    double_rooms = Column(Integer)
    
    # Budget
    section = Column(String(10))
    budget_code = Column(String(50))
    activity_code = Column(String(50))
    cost_center = Column(String(50))
    
    # Metadata
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    attachments = relationship("EventAttachment", back_populates="event", cascade="all, delete-orphan")
    certificates = relationship("EventCertificate", back_populates="event", cascade="all, delete-orphan")
    badges = relationship("EventBadge", back_populates="event", cascade="all, delete-orphan")
    venue = relationship("VendorAccommodation", foreign_keys=[vendor_accommodation_id])
    passport_records = relationship("PassportRecord", back_populates="event", cascade="all, delete-orphan")
    chat_rooms = relationship("ChatRoom", back_populates="event", cascade="all, delete-orphan")
    form_fields = relationship("FormField", back_populates="event", cascade="all, delete-orphan")
    vetting_member_selections = relationship("VettingMemberSelection", back_populates="event", cascade="all, delete-orphan")