from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class VettingMemberSelection(Base):
    __tablename__ = "vetting_member_selections"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id", ondelete="CASCADE"), nullable=False)
    member_email = Column(String(255), nullable=False, index=True)
    selection = Column(String(20), nullable=False)  # 'selected', 'not_selected'
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    event = relationship("Event", back_populates="vetting_member_selections")
    participant = relationship("EventParticipant", back_populates="vetting_member_selections")

    # Unique constraint to ensure one selection per member per participant
    __table_args__ = (
        UniqueConstraint('event_id', 'participant_id', 'member_email', name='unique_member_participant_selection'),
    )


class VettingMemberComment(Base):
    """Stores comment history for vetting discussions on participants."""
    __tablename__ = "vetting_member_comments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    author_email = Column(String(255), nullable=False, index=True)
    author_name = Column(String(255), nullable=False)
    author_role = Column(String(50), nullable=False)  # 'committee_member', 'approver'
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    event = relationship("Event")
    participant = relationship("EventParticipant")
