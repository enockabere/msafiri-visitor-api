from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatRoomBase(BaseModel):
    name: str
    chat_type: str  # "direct_message" or "event_chatroom"
    event_id: Optional[int] = None

class ChatRoomCreate(ChatRoomBase):
    pass

class ChatRoom(ChatRoomBase):
    id: int
    tenant_id: int
    is_active: bool
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    message: str

class MessageCreate(MessageBase):
    chat_room_id: int
    reply_to_message_id: Optional[int] = None

class ReplyToMessage(BaseModel):
    id: int
    sender_name: str
    message: str

class ChatMessage(MessageBase):
    id: int
    chat_room_id: int
    sender_email: str
    sender_name: str
    reply_to_message_id: Optional[int] = None
    reply_to: Optional[ReplyToMessage] = None
    is_admin_message: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class DirectMessageCreate(BaseModel):
    recipient_email: str
    message: str
    reply_to_message_id: Optional[int] = None

class DirectMessage(BaseModel):
    id: int
    sender_email: str
    sender_name: str
    recipient_email: str
    recipient_name: str
    message: str
    reply_to_message_id: Optional[int] = None
    reply_to: Optional[ReplyToMessage] = None
    is_read: bool
    tenant_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatRoomWithMessages(ChatRoom):
    messages: List[ChatMessage] = []

class WebSocketMessage(BaseModel):
    type: str  # "message", "join", "leave"
    chat_room_id: Optional[int] = None
    message: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None