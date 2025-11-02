from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class PassportRecord(BaseModel):
    __tablename__ = "passport_records"

    user_email = Column(String, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    record_id = Column(Integer, nullable=False, unique=True)  # External API record ID
    
    # Relationships
    event = relationship("Event", back_populates="passport_records")