from sqlalchemy import Column, String, Integer, ForeignKey, Text
from app.models.base import BaseModel

class SecurityBriefing(BaseModel):
    __tablename__ = "security_briefings"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    document_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    created_by = Column(String(255), nullable=False)