from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base_class import Base


class BadgeTemplate(Base):
    __tablename__ = "badge_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    template_content = Column(Text)  # HTML template content
    logo_url = Column(String(500))
    logo_public_id = Column(String(255))
    background_url = Column(String(500))
    background_public_id = Column(String(255))
    enable_qr_code = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    badge_size = Column(String(50), default="standard")  # standard, large, small
    orientation = Column(String(20), default="portrait")  # portrait, landscape
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())