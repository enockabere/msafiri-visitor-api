from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Date
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class EventCheckin(BaseModel):
    __tablename__ = "event_checkins"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    checkin_date = Column(Date, nullable=False)
    checkin_time = Column(DateTime, nullable=False)
    checked_in_by = Column(String(255), nullable=False)  # Admin who scanned QR
    qr_token_used = Column(String(255), nullable=False)
    badge_printed = Column(Boolean, default=False)
    badge_printed_at = Column(DateTime)
    notes = Column(Text)
    
    # Relationships
    participant = relationship("EventParticipant")
    event = relationship("Event")

class EquipmentRequest(BaseModel):
    __tablename__ = "equipment_requests"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    equipment_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    description = Column(Text)
    urgency = Column(String(20), default="normal")  # low, normal, high, urgent
    status = Column(String(20), default="pending")  # pending, approved, fulfilled, rejected
    admin_notes = Column(Text)
    approved_by = Column(String(255))
    fulfilled_by = Column(String(255))
    fulfilled_at = Column(DateTime)
    
    # Relationships
    participant = relationship("EventParticipant")
    event = relationship("Event")

class EventReview(BaseModel):
    __tablename__ = "event_reviews"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    overall_rating = Column(Integer, nullable=False)  # 1-5 stars
    content_rating = Column(Integer)  # 1-5 stars
    organization_rating = Column(Integer)  # 1-5 stars
    venue_rating = Column(Integer)  # 1-5 stars
    catering_rating = Column(Integer)  # 1-5 stars
    review_text = Column(Text)
    suggestions = Column(Text)
    would_recommend = Column(Boolean)
    
    # Relationships
    participant = relationship("EventParticipant")
    event = relationship("Event")

class AppReview(BaseModel):
    __tablename__ = "app_reviews"
    
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255), nullable=False)
    overall_rating = Column(Integer, nullable=False)  # 1-5 stars
    ease_of_use = Column(Integer)  # 1-5 stars
    functionality_rating = Column(Integer)  # 1-5 stars
    design_rating = Column(Integer)  # 1-5 stars
    review_text = Column(Text)
    suggestions = Column(Text)
    device_type = Column(String(50))  # mobile, tablet, desktop
    app_version = Column(String(20))