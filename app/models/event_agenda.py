from sqlalchemy import Column, String, Integer, ForeignKey, Text, Date, Time
from app.models.base import BaseModel

class EventAgenda(BaseModel):
    __tablename__ = "event_agenda"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    day_number = Column(Integer, nullable=False)  # Day 1, 2, 3, etc.
    event_date = Column(Date, nullable=False)
    time = Column(String(10), nullable=False)  # "09:00", "14:30", etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)