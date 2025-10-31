from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class TravelChecklistProgress(Base):
    __tablename__ = "travel_checklist_progress"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    checklist_items = Column(JSON, nullable=False, default={})
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())