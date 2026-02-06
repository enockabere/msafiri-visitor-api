from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class EventAttachment(BaseModel):
    __tablename__ = "event_attachments"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_by = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    public_id = Column(String(255), nullable=True)  # Cloudinary public_id
    file_type = Column(String(100), nullable=True)  # MIME type
    resource_type = Column(String(50), nullable=True)  # image/raw
    original_filename = Column(String(255), nullable=True)  # Original filename
    
    # Relationships
    event = relationship("Event", back_populates="attachments")
