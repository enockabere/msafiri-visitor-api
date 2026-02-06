from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class ChatType(enum.Enum):
    DIRECT_MESSAGE = "direct_message"
    EVENT_CHATROOM = "event_chatroom"
    VETTING_CHAT = "vetting_chat"

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
    event = relationship("Event", back_populates="chat_rooms")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")
    vetting_chat = relationship("VettingChatRoom", back_populates="chat_room", uselist=False, cascade="all, delete-orphan")


class VettingChatRoom(Base):
    """Extended chat room data for vetting committee discussions."""
    __tablename__ = "vetting_chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, unique=True)
    vetting_committee_id = Column(Integer, ForeignKey("vetting_committees.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)

    # Chat status tracking
    is_locked = Column(Boolean, default=False)  # Locked when vetting is approved
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_reason = Column(String(100), nullable=True)  # 'approved', 'event_ended'

    # Deletion tracking
    event_end_date = Column(Date, nullable=True)
    scheduled_deletion_date = Column(Date, nullable=True)  # 30 days after event end

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="vetting_chat")
    vetting_committee = relationship("VettingCommittee")
    event = relationship("Event")
    members = relationship("VettingChatMember", back_populates="vetting_chat", cascade="all, delete-orphan")


class VettingChatMember(Base):
    """Tracks vetting chat members and their chat permissions."""
    __tablename__ = "vetting_chat_members"

    id = Column(Integer, primary_key=True, index=True)
    vetting_chat_id = Column(Integer, ForeignKey("vetting_chat_rooms.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'committee_member', 'approver'

    # Chat permission tracking
    can_send_messages = Column(Boolean, default=True)
    muted_at = Column(DateTime(timezone=True), nullable=True)
    muted_reason = Column(String(100), nullable=True)  # 'submitted_vetting', 'approved_vetting'

    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vetting_chat = relationship("VettingChatRoom", back_populates="members")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_email = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)  # Now nullable as message could be just an attachment
    reply_to_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    is_admin_message = Column(Boolean, default=False)
    # File attachment fields
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)  # 'image', 'document', 'voice', 'video'
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds (for voice/video)
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
    message = Column(Text, nullable=True)  # Now nullable as message could be just an attachment
    reply_to_message_id = Column(Integer, ForeignKey("direct_messages.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    tenant_id = Column(String(50), nullable=False)
    # File attachment fields
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)  # 'image', 'document', 'voice', 'video'
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds (for voice/video)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reply_to = relationship("DirectMessage", remote_side=[id])
