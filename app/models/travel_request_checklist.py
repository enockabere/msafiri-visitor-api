from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class TravelRequestChecklist(Base):
    __tablename__ = "travel_request_checklists"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    traveler_name = Column(String(255), nullable=False)
    nationality = Column(String(100), nullable=True)
    destination_tenants = Column(JSONB, nullable=True)  # List of tenant slugs
    checklist_items = Column(JSONB, nullable=False)  # List of checklist items with has_item status
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    travel_request = relationship("TravelRequest", back_populates="checklists")
