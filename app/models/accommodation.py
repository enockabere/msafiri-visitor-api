from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class RoomType(enum.Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SHARED = "shared"
    SUITE = "suite"

class RoomAssignment(BaseModel):
    __tablename__ = "room_assignments"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    hotel_name = Column(String(255), nullable=False)
    room_number = Column(String(50), nullable=False)
    room_type = Column(Enum(RoomType), nullable=False)
    floor = Column(String(10))
    building = Column(String(100))
    address = Column(Text, nullable=False)
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime, nullable=False)
    room_agent_email = Column(String(255))  # Agent who manages this room
    
    # Check-in status
    checked_in = Column(Boolean, default=False)
    checked_in_by = Column(String(255))  # Who checked them in
    check_in_time = Column(DateTime)
    admin_checked_in = Column(Boolean, default=False)
    
    # Room details
    amenities = Column(Text)  # JSON string of amenities
    wifi_password = Column(String(100))
    special_instructions = Column(Text)
    
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="room_assignment")

class RoomAgent(BaseModel):
    __tablename__ = "room_agents"
    
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    hotel_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), nullable=False)
    api_token = Column(String(255), unique=True)
    created_by = Column(String(255), nullable=False)

class RoomRules(BaseModel):
    __tablename__ = "room_rules"
    
    hotel_name = Column(String(255), nullable=False)
    rule_title = Column(String(255), nullable=False)
    rule_description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    updated_by = Column(String(255))