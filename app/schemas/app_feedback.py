from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.app_feedback import FeedbackCategory

class AppFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    category: FeedbackCategory
    feedback_text: str = Field(..., min_length=1, max_length=2000)

class AppFeedbackResponse(BaseModel):
    id: int
    user_id: int
    rating: int
    category: FeedbackCategory
    feedback_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # User info
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True