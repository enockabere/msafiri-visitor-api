from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    image_url: Optional[str] = None


class ToolResult(BaseModel):
    tool_name: str
    result: Any


class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    tool_results: List[ToolResult] = []
    conversation_title: str = "New Conversation"


class ConversationMessageResponse(BaseModel):
    id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[Any] = None
    tool_results: Optional[Any] = None
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse] = []

    class Config:
        from_attributes = True
