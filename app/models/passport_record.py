from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import hashlib
import secrets

class PassportRecord(BaseModel):
    __tablename__ = "passport_records"

    user_email = Column(String, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    record_id = Column(Integer, nullable=False, unique=True)  # External API record ID
    slug = Column(String, nullable=True, unique=True, index=True)  # URL-safe slug
    
    # Relationships
    event = relationship("Event", back_populates="passport_records")
    
    def generate_slug(self):
        """Generate a unique slug for this passport record"""
        if not self.slug:
            # Create a hash from record_id, user_email, and a random salt
            salt = secrets.token_hex(8)
            data = f"{self.record_id}-{self.user_email}-{salt}"
            self.slug = hashlib.sha256(data.encode()).hexdigest()[:16]
        return self.slug