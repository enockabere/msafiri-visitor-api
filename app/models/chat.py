from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class ChatType(enum.Enum):
    DIRECT_MESSAGE = "direct_message"
    EVENT_CHATROOM = "event_chatroom"

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_type = Column(Enum(ChatType), nullable=False)
    name = Column(String(255), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Only for event chatrooms
    tenant_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    event = relationship("Event")
    messages = relationship("ChatMessage", back_populates="chat_room")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    reply_to_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    is_admin_message = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    reply_to = relationship("ChatMessage", remote_side=[id])

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    tenant_id = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())