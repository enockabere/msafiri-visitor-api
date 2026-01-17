from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class FormField(Base):
    __tablename__ = "form_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, email, select, checkbox, textarea, radio, date
    field_options = Column(Text, nullable=True)  # JSON string for select options
    is_required = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_protected = Column(Boolean, default=False)  # Protected fields cannot be deleted
    section = Column(String(50), nullable=True)  # personal, contact, travel, final
    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    event = relationship("Event", back_populates="form_fields")
    responses = relationship("FormResponse", back_populates="field", cascade="all, delete-orphan")

class FormResponse(Base):
    __tablename__ = "form_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    registration_id = Column(Integer, ForeignKey("event_participants.id", ondelete="CASCADE"), nullable=False)
    field_id = Column(Integer, ForeignKey("form_fields.id", ondelete="CASCADE"), nullable=False)
    field_value = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    field = relationship("FormField", back_populates="responses")
    participant = relationship("EventParticipant", foreign_keys=[registration_id])