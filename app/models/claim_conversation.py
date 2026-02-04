from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ClaimConversation(Base):
    __tablename__ = "claim_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship(
        "ClaimConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ClaimConversationMessage.created_at",
    )


class ClaimConversationMessage(Base):
    __tablename__ = "claim_conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("claim_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'tool'
    content = Column(Text)
    tool_calls = Column(JSON)
    tool_results = Column(JSON)
    image_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("ClaimConversation", back_populates="messages")
