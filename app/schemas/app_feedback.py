from pydantic import BaseModel, Field, validator
from typing import Optional, Union
from datetime import datetime
from app.models.app_feedback import FeedbackCategory

class AppFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    category: Union[FeedbackCategory, str]
    feedback_text: str = Field(..., min_length=1, max_length=2000)
    
    @validator('category', pre=True)
    def validate_category(cls, v):
        if isinstance(v, str):
            # Convert string to enum by value
            for category in FeedbackCategory:
                if category.value == v.lower():
                    return category
            # If not found by value, try by name (for backward compatibility)
            try:
                return FeedbackCategory[v.upper()]
            except KeyError:
                raise ValueError(f"Invalid category: {v}")
        return v

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