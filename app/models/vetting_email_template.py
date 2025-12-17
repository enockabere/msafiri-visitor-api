# File: app/models/vetting_email_template.py
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class TemplateType(enum.Enum):
    SELECTED = "selected"
    NOT_SELECTED = "not_selected"

class VettingEmailTemplate(BaseModel):
    __tablename__ = "vetting_email_templates"

    committee_id = Column(Integer, ForeignKey("vetting_committees.id", ondelete="CASCADE"), nullable=False)
    template_type = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(String(255), nullable=False)

    # Relationships
    committee = relationship("VettingCommittee", foreign_keys=[committee_id])
