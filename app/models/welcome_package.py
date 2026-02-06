from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class EventWelcomePackage(BaseModel):
    __tablename__ = "event_welcome_packages"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    description = Column(Text)
    quantity_per_participant = Column(Integer, default=1)
    is_functional_phone = Column(Boolean, default=False)
    pickup_instructions = Column(Text)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")

class ParticipantWelcomeDelivery(BaseModel):
    __tablename__ = "participant_welcome_deliveries"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    package_item_id = Column(Integer, ForeignKey("event_welcome_packages.id"), nullable=False)
    delivered = Column(Boolean, default=False)
    delivered_by = Column(String(255))  # Driver who delivered
    delivery_notes = Column(Text)
    
    # Relationships
    participant = relationship("EventParticipant")
    package_item = relationship("EventWelcomePackage")
