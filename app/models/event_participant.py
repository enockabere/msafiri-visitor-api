from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class ParticipantRole(enum.Enum):
    ATTENDEE = "attendee"
    SPEAKER = "speaker"
    ORGANIZER = "organizer"
    VIP = "vip"

class ParticipantStatus(enum.Enum):
    REGISTERED = "registered"  # User self-registered
    SELECTED = "selected"     # Admin selected for event
    NOT_SELECTED = "not_selected"  # Admin rejected
    WAITING = "waiting"       # On waiting list
    CANCELED = "canceled"     # Registration canceled
    ATTENDED = "attended"     # Actually attended
    CONFIRMED = "confirmed"   # User confirmed attendance
    DECLINED = "declined"     # User declined attendance

class DeclineReason(enum.Enum):
    NO_SHOW = "No Show"
    DECLINED_OPERATIONAL = "Declined - Operational / Work Reasons"
    DECLINED_PERSONAL = "Declined - Personal Reasons"
    CANCELLED_OPERATIONAL = "Cancelled - Operational Reasons"
    CANCELLED_PERSONAL = "Cancelled - Personal Reasons"
    CANCELLED_PRIORITISING_TRAINING = "Cancelled - Prioritising Other Training"
    CANCELLED_VISA_REJECTED = "Cancelled - Visa Rejected"
    CANCELLED_VISA_APPOINTMENT = "Cancelled - Visa Appointment Not Available"
    CANCELLED_VISA_DELAY = "Cancelled - Visa Issuing Took Too Long"
    CANCELLED_VISA_UNFEASIBLE = "Cancelled - Visa Process Unfeasible"
    CANCELLATION = "Cancellation"

class EventParticipant(BaseModel):
    __tablename__ = "event_participants"
    
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Link to user account
    email = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default='attendee')
    participant_role = Column(String(50), default='visitor')  # Event-specific role: visitor, facilitator, organizer
    status = Column(String(50), default='registered')  # Default to registered
    # registration_type = Column(String(50), default='self')  # 'self' or 'admin'
    invited_by = Column(String(255), nullable=False)  # Keep original column name for now
    # notes = Column(Text, nullable=True)  # Admin notes
    
    # Registration details
    country = Column(String(100), nullable=True)
    nationality = Column(String(100), nullable=True)
    position = Column(String(255), nullable=True)
    project = Column(String(255), nullable=True)
    gender = Column(String(50), nullable=True)
    eta = Column(String(255), nullable=True)  # Expected Time of Arrival
    requires_eta = Column(Boolean, default=False)
    
    # Document upload tracking
    passport_document = Column(String(500), nullable=True)
    ticket_document = Column(String(500), nullable=True)
    
    # Public registration form fields
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    oc = Column(String(50), nullable=True)
    contract_status = Column(String(100), nullable=True)
    contract_type = Column(String(100), nullable=True)
    gender_identity = Column(String(100), nullable=True)
    sex = Column(String(50), nullable=True)
    pronouns = Column(String(50), nullable=True)
    current_position = Column(String(255), nullable=True)
    country_of_work = Column(String(255), nullable=True)
    project_of_work = Column(String(255), nullable=True)
    personal_email = Column(String(255), nullable=True)
    msf_email = Column(String(255), nullable=True)
    hrco_email = Column(String(255), nullable=True)
    career_manager_email = Column(String(255), nullable=True)
    ld_manager_email = Column(String(255), nullable=True)
    line_manager_email = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    travelling_internationally = Column(String(10), nullable=True)
    accommodation_needs = Column(Text, nullable=True)
    daily_meals = Column(String(255), nullable=True)
    certificate_name = Column(String(255), nullable=True)
    badge_name = Column(String(255), nullable=True)
    motivation_letter = Column(Text, nullable=True)
    code_of_conduct_confirm = Column(String(10), nullable=True)
    travel_requirements_confirm = Column(String(10), nullable=True)
    
    # Legacy registration form fields
    dietary_requirements = Column(Text, nullable=True)
    accommodation_type = Column(String(100), nullable=True)
    participant_name = Column(String(255), nullable=True)
    participant_email = Column(String(255), nullable=True)
    
    # Travel and accommodation preferences
    accommodation_preference = Column(String(100), nullable=True)
    has_dietary_requirements = Column(Boolean, default=False)
    has_accommodation_needs = Column(Boolean, default=False)
    
    # Invitation tracking fields (will be added to DB later)
    # invitation_sent = Column(Boolean, default=False)
    # invitation_sent_at = Column(DateTime, nullable=True)
    # invitation_accepted = Column(Boolean, default=False)
    # invitation_accepted_at = Column(DateTime, nullable=True)
    
    # Decline tracking fields
    decline_reason = Column(Enum(DeclineReason), nullable=True)
    declined_at = Column(DateTime, nullable=True)
    
    # Vetting comments
    vetting_comments = Column(Text, nullable=True)
    
    # Confirmation tracking
    confirmed_at = Column(DateTime, nullable=True)
    
    # Proof of accommodation tracking
    proof_of_accommodation_url = Column(String(500), nullable=True)
    proof_generated_at = Column(DateTime, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="participants")
    # user = relationship("User", foreign_keys=[user_id])