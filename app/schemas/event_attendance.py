from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, date

class EventCheckinCreate(BaseModel):
    qr_token: str
    notes: Optional[str] = None

class EventCheckin(BaseModel):
    id: int
    participant_id: int
    event_id: int
    checkin_date: date
    checkin_time: datetime
    checked_in_by: str
    badge_printed: bool
    badge_printed_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class EquipmentRequestCreate(BaseModel):
    event_id: int
    equipment_name: str
    quantity: int = 1
    description: Optional[str] = None
    urgency: str = "normal"

class EquipmentRequest(BaseModel):
    id: int
    participant_id: int
    event_id: int
    equipment_name: str
    quantity: int
    description: Optional[str] = None
    urgency: str
    status: str
    admin_notes: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventReviewCreate(BaseModel):
    event_id: int
    overall_rating: int
    content_rating: Optional[int] = None
    organization_rating: Optional[int] = None
    venue_rating: Optional[int] = None
    catering_rating: Optional[int] = None
    review_text: Optional[str] = None
    suggestions: Optional[str] = None
    would_recommend: Optional[bool] = None
    
    @validator('overall_rating', 'content_rating', 'organization_rating', 'venue_rating', 'catering_rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class EventReview(BaseModel):
    id: int
    participant_id: int
    event_id: int
    overall_rating: int
    content_rating: Optional[int] = None
    organization_rating: Optional[int] = None
    venue_rating: Optional[int] = None
    catering_rating: Optional[int] = None
    review_text: Optional[str] = None
    suggestions: Optional[str] = None
    would_recommend: Optional[bool] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AppReviewCreate(BaseModel):
    overall_rating: int
    ease_of_use: Optional[int] = None
    functionality_rating: Optional[int] = None
    design_rating: Optional[int] = None
    review_text: Optional[str] = None
    suggestions: Optional[str] = None
    device_type: Optional[str] = None
    app_version: Optional[str] = None
    
    @validator('overall_rating', 'ease_of_use', 'functionality_rating', 'design_rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class AppReview(BaseModel):
    id: int
    user_email: str
    user_name: str
    overall_rating: int
    ease_of_use: Optional[int] = None
    functionality_rating: Optional[int] = None
    design_rating: Optional[int] = None
    review_text: Optional[str] = None
    suggestions: Optional[str] = None
    device_type: Optional[str] = None
    app_version: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceStats(BaseModel):
    event_id: int
    event_title: str
    total_participants: int
    total_checkins: int
    attendance_rate: float
    daily_checkins: list
    badges_printed: int

class BadgePrintData(BaseModel):
    participant_name: str
    participant_email: str
    event_title: str
    checkin_date: str
    qr_code: str

class EquipmentRequestAction(BaseModel):
    status: str  # approved, fulfilled, rejected
    admin_notes: Optional[str] = None
