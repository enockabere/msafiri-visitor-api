from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class ContactType(enum.Enum):
    EMERGENCY = "emergency"
    MEDICAL = "medical"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    EVENT_STAFF = "event_staff"
    GENERAL = "general"

class EventContact(BaseModel):
    __tablename__ = "event_contacts"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    contact_type = Column(Enum(ContactType), nullable=False)
    name = Column(String(255), nullable=False)
    title = Column(String(255))
    phone = Column(String(50), nullable=False)
    email = Column(String(255))
    department = Column(String(255))
    availability = Column(String(255))  # "24/7", "9AM-5PM", etc.
    is_primary = Column(Boolean, default=False)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    event = relationship("Event")

class ParticipantProfile(BaseModel):
    __tablename__ = "participant_profiles"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, unique=True)
    dietary_restrictions = Column(Text)  # JSON array of restrictions
    food_allergies = Column(Text)  # JSON array of allergies
    medical_conditions = Column(Text)  # JSON array of conditions
    mobility_requirements = Column(Text)
    special_requests = Column(Text)
    emergency_contact_name = Column(String(255))
    emergency_contact_phone = Column(String(50))
    emergency_contact_relationship = Column(String(100))
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="profile")

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class ChatMessageStatus(BaseModel):
    __tablename__ = "chat_message_status"
    
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    status_timestamp = Column(DateTime, nullable=False)
    
    # Relationships
    message = relationship("ChatMessage")

class NotificationType(enum.Enum):
    PICKUP_CONFIRMED = "pickup_confirmed"
    ROOM_ASSIGNED = "room_assigned"
    RIDE_ASSIGNED = "ride_assigned"
    PERDIEM_APPROVED = "perdiem_approved"
    EQUIPMENT_FULFILLED = "equipment_fulfilled"
    SECURITY_BRIEF_ADDED = "security_brief_added"
    EVENT_REMINDER = "event_reminder"

class NotificationQueue(BaseModel):
    __tablename__ = "notification_queue"
    
    recipient_email = Column(String(255), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text)  # JSON data for notification
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    failed_attempts = Column(Integer, default=0)