# File: app/models/vetting_deadline_reminder.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class VettingDeadlineReminder(BaseModel):
    __tablename__ = "vetting_deadline_reminders"

    committee_id = Column(Integer, ForeignKey("vetting_committees.id", ondelete="CASCADE"), nullable=False)
    reminder_type = Column(String(50), nullable=False)
    recipients_count = Column(Integer, nullable=True)

    # Relationships
    committee = relationship("VettingCommittee")
