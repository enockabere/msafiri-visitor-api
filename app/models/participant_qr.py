from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base

class ParticipantQR(Base):
    __tablename__ = "participant_qr_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, unique=True)
    qr_token = Column(String(255), nullable=False, unique=True)
    qr_data = Column(Text, nullable=False)  # JSON string with allocation data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
