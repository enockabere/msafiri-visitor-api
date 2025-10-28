from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.models.news_update import NewsCategory

class NewsUpdateBase(BaseModel):
    title: str
    summary: str
    content: Optional[str] = None
    external_link: Optional[str] = None
    content_type: str = "text"  # "text" or "link"
    category: NewsCategory
    is_important: bool = False
    scheduled_publish_at: Optional[datetime] = None
    image_url: Optional[str] = None

class NewsUpdateCreate(NewsUpdateBase):
    pass

class NewsUpdateUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    external_link: Optional[str] = None
    content_type: Optional[str] = None
    category: Optional[NewsCategory] = None
    is_important: Optional[bool] = None
    scheduled_publish_at: Optional[datetime] = None
    image_url: Optional[str] = None

class NewsUpdatePublish(BaseModel):
    is_published: bool

class NewsUpdateResponse(NewsUpdateBase):
    id: int
    tenant_id: int
    is_published: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NewsUpdateListResponse(BaseModel):
    items: list[NewsUpdateResponse]
    total: int
    page: int
    size: int
    pages: int