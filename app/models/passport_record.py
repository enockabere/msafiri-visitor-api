from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import hashlib
import secrets
from datetime import datetime, timedelta

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
    deletion_date = Column(DateTime, nullable=True)  # Auto-deletion date (30 days after event ends)

    # Relationships
    event = relationship("Event", back_populates="passport_records")
    
    def set_deletion_date(self, event_end_date):
        """Set deletion date to 30 days after event ends"""
        if event_end_date:
            if isinstance(event_end_date, str):
                event_end_date = datetime.fromisoformat(event_end_date.replace('Z', '+00:00'))
            self.deletion_date = event_end_date + timedelta(days=30)
    
    def days_until_deletion(self):
        """Calculate days remaining until deletion"""
        if not self.deletion_date:
            return None
        delta = self.deletion_date - datetime.utcnow()
        return max(0, delta.days)

    def generate_slug(self):
        """Generate a unique slug for this passport record"""
        if not self.slug:
            # Create a hash from record_id, user_email, and a random salt
            salt = secrets.token_hex(8)
            data = f"{self.record_id}-{self.user_email}-{salt}"
            self.slug = hashlib.sha256(data.encode()).hexdigest()[:16]
        return self.slug
    
    def to_dict_with_countdown(self):
        """Convert to dict with deletion countdown"""
        return {
            'id': self.id,
            'passport_number': self.passport_number,
            'given_names': self.given_names,
            'surname': self.surname,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth,
            'date_of_expiry': self.date_of_expiry,
            'date_of_issue': self.date_of_issue,
            'gender': self.gender,
            'nationality': self.nationality,
            'issue_country': self.issue_country,
            'deletion_date': self.deletion_date.isoformat() if self.deletion_date else None,
            'days_until_deletion': self.days_until_deletion(),
        }

    @property
    def full_name(self):
        """Get full name from given_names and surname"""
        if self.given_names and self.surname:
            return f"{self.given_names} {self.surname}"
        return self.given_names or self.surname or ""
