from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import hashlib
import secrets

class PassportRecord(BaseModel):
    __tablename__ = "passport_records"

    user_email = Column(String, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    record_id = Column(Integer, nullable=False, unique=True)  # Record ID (now locally generated)
    slug = Column(String, nullable=True, unique=True, index=True)  # URL-safe slug

    # Passport data fields (stored locally since we use Document Intelligence)
    passport_number = Column(String(50), nullable=True)
    given_names = Column(String(255), nullable=True)
    surname = Column(String(255), nullable=True)
    date_of_birth = Column(String(20), nullable=True)  # YYYY-MM-DD format
    date_of_expiry = Column(String(20), nullable=True)  # YYYY-MM-DD format
    date_of_issue = Column(String(20), nullable=True)  # YYYY-MM-DD format
    gender = Column(String(10), nullable=True)
    nationality = Column(String(100), nullable=True)
    issue_country = Column(String(100), nullable=True)
    passport_image_url = Column(Text, nullable=True)  # Azure Blob URL

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

    @property
    def full_name(self):
        """Get full name from given_names and surname"""
        if self.given_names and self.surname:
            return f"{self.given_names} {self.surname}"
        return self.given_names or self.surname or ""
