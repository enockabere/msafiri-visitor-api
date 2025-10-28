from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List
import json
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.chat import ChatRoom, ChatMessage, DirectMessage, ChatType
from app.models.user import User
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.schemas.chat import (
    ChatRoomCreate, ChatRoom as ChatRoomSchema, ChatMessage as MessageSchema,
    DirectMessageCreate, DirectMessage as DirectMessageSchema,
    MessageCreate, ChatRoomWithMessages, WebSocketMessage
)
from app.api.deps import get_current_user, get_tenant_context
from app.core.websocket_manager import manager, notification_manager

router = APIRouter()

# Chat Room Management
@router.post("/rooms/", response_model=ChatRoomSchema)
def create_chat_room(
    room: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create chat room - admins only"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role.upper() not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_room = ChatRoom(
        **room.dict(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.email
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/rooms/", response_model=List[ChatRoomSchema])
def get_chat_rooms(
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available chat rooms - auto-create missing event rooms and show rooms for user's events"""
    # Auto-create chat rooms for events that don't have them
    events_without_rooms = db.query(Event).outerjoin(
        ChatRoom, and_(Event.id == ChatRoom.event_id, ChatRoom.chat_type == ChatType.EVENT_CHATROOM)
    ).filter(
        ChatRoom.id.is_(None)
    ).all()
    
    created_rooms = []
    for event in events_without_rooms:
        room = ChatRoom(
            name=f"{event.title} - Event Chat",
            chat_type=ChatType.EVENT_CHATROOM,
            event_id=event.id,
            tenant_id=event.tenant_id,  # Use integer to match model
            created_by="system"
        )
        db.add(room)
        created_rooms.append(room)
    
    if created_rooms:
        db.commit()
        print(f"AUTO-CREATED: {len(created_rooms)} chat rooms for events")
    
    # Get events user is participating in
    user_event_ids = db.query(EventParticipant.event_id).filter(
        EventParticipant.user_email == current_user.email
    ).subquery()
    
    # Get chat rooms for user's events only
    query = db.query(ChatRoom).filter(
        and_(
            ChatRoom.is_active == True,
            ChatRoom.event_id.in_(user_event_ids)
        )
    )
    
    if event_id:
        query = query.filter(ChatRoom.event_id == event_id)
    
    query = query.order_by(ChatRoom.created_at.desc())
    
    rooms = query.all()
    print(f"DEBUG: Found {len(rooms)} chat rooms for user {current_user.email}")
    for room in rooms:
        print(f"DEBUG: Room: {room.name}, Event ID: {room.event_id}, Tenant: {room.tenant_id}")
    
    return rooms

@router.post("/rooms/auto-create")
def auto_create_event_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-create chat rooms for events that don't have them"""
    
    # Get all events without chat rooms
    events_without_rooms = db.query(Event).outerjoin(
        ChatRoom, and_(Event.id == ChatRoom.event_id, ChatRoom.chat_type == ChatType.EVENT_CHATROOM)
    ).filter(
        ChatRoom.id.is_(None)
    ).all()
    
    created_rooms = []
    for event in events_without_rooms:
        room = ChatRoom(
            name=f"{event.title} - Event Chat",
            chat_type=ChatType.EVENT_CHATROOM,
            event_id=event.id,
            tenant_id=event.tenant_id,
            created_by=current_user.email
        )
        db.add(room)
        created_rooms.append(room)
    
    if created_rooms:
        db.commit()
    
    return {"message": f"Created {len(created_rooms)} chat rooms", "rooms": len(created_rooms)}

@router.post("/messages/", response_model=MessageSchema)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send message to chat room - allow cross-tenant messaging"""
    room = db.query(ChatRoom).filter(
        and_(
            ChatRoom.id == message.chat_room_id,
            ChatRoom.is_active == True
        )
    ).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if room.event_id:
        event = db.query(Event).filter(Event.id == room.event_id).first()
        if event and event.end_date < datetime.now().date():
            raise HTTPException(status_code=403, detail="Cannot send messages to ended event chat")
    
    sender_name = current_user.full_name or current_user.email
    print(f"DEBUG: Creating message with sender_name: {sender_name} for user: {current_user.email}")
    
    db_message = ChatMessage(
        chat_room_id=message.chat_room_id,
        sender_email=current_user.email,
        sender_name=sender_name,
        message=message.message,
        reply_to_message_id=getattr(message, 'reply_to_message_id', None),
        is_admin_message=(current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)).upper() in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Send real-time notification to all users in the tenant
    await notification_manager.broadcast_chat_notification({
        "type": "chat_message",
        "data": {
            "chat_room_id": room.id,
            "chat_room_name": room.name,
            "sender_name": sender_name,
            "message": message.message,
            "timestamp": str(db_message.created_at)
        }
    }, current_user.tenant_id, exclude_user=current_user.email)
    
    # Send in-app notification to portal users
    try:
        from app.crud.notification import notification
        
        print(f"CHAT: Creating in-app notifications for message in room {room.name}")
        
        # Get all users in the tenant except sender
        tenant_users = db.query(User).filter(
            and_(
                User.tenant_id == current_user.tenant_id,
                User.email != current_user.email,
                User.is_active == True
            )
        ).all()
        
        print(f"CHAT: Found {len(tenant_users)} users to notify")
        
        for user in tenant_users:
            print(f"CHAT: Creating notification for user {user.email}")
            print(f"CHAT: User tenant_id: {user.tenant_id}, Current user tenant_id: {current_user.tenant_id}")
            try:
                created_notification = notification.create_user_notification(
                    db=db,
                    user_id=user.id,
                    title=f"New message in {room.name}",
                    message=f"{sender_name}: {message.message[:100]}{'...' if len(message.message) > 100 else ''}",
                    tenant_id=user.tenant_id,
                    notification_type="CHAT_MESSAGE",
                    priority="LOW",
                    send_email=False,
                    send_push=False,
                    action_url=f"/tenant/{current_user.tenant_id}/chat",
                    triggered_by=current_user.email
                )
                print(f"CHAT: Created notification ID {created_notification.id} for user {user.email}")
            except Exception as user_error:
                print(f"CHAT ERROR: Failed to create notification for user {user.email}: {user_error}")
                import traceback
                traceback.print_exc()
            
        print(f"CHAT: Successfully created {len(tenant_users)} in-app notifications")
    except Exception as e:
        print(f"CHAT ERROR: Failed to create in-app notifications: {e}")
        import traceback
        traceback.print_exc()
        # Rollback the session to prevent transaction issues
        try:
            db.rollback()
        except Exception as rollback_error:
            print(f"CHAT ERROR: Failed to rollback session: {rollback_error}")
    
    return db_message

@router.get("/rooms/{room_id}/messages", response_model=List[MessageSchema])
def get_room_messages(
    room_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat room messages with reply context - allow cross-tenant access"""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_room_id == room_id
    ).order_by(desc(ChatMessage.created_at)).limit(limit).all()
    
    # Add reply context to messages
    result_messages = []
    for message in messages:
        message_dict = {
            "id": message.id,
            "chat_room_id": message.chat_room_id,
            "sender_email": message.sender_email,
            "sender_name": message.sender_name,
            "message": message.message,
            "reply_to_message_id": message.reply_to_message_id,
            "is_admin_message": message.is_admin_message,
            "created_at": message.created_at,
            "reply_to": None
        }
        
        if message.reply_to_message_id:
            reply_to = db.query(ChatMessage).filter(
                ChatMessage.id == message.reply_to_message_id
            ).first()
            if reply_to:
                message_dict["reply_to"] = {
                    "id": reply_to.id,
                    "sender_name": reply_to.sender_name,
                    "message": reply_to.message
                }
        
        result_messages.append(message_dict)
    
    return result_messages

@router.get("/rooms/{room_id}/status")
def get_room_status(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat room status - allow cross-tenant access"""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    can_send_messages = True
    event_status = "active"
    
    if room.event_id:
        event = db.query(Event).filter(Event.id == room.event_id).first()
        if event:
            now = datetime.now().date()
            if event.end_date < now:
                can_send_messages = False
                event_status = "ended"
            elif event.start_date > now:
                event_status = "upcoming"
            else:
                event_status = "ongoing"
    
    return {
        "room_id": room_id,
        "can_send_messages": can_send_messages,
        "event_status": event_status,
        "room_name": room.name
    }

@router.delete("/cleanup-ended-events")
def cleanup_ended_event_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cleanup chat rooms for events ended more than 1 week ago"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role.upper() not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    one_week_ago = datetime.now() - timedelta(days=7)
    
    rooms_to_delete = db.query(ChatRoom).join(Event).filter(
        and_(
            ChatRoom.tenant_id == current_user.tenant_id,
            ChatRoom.chat_type == ChatType.EVENT_CHATROOM,
            Event.end_date < one_week_ago
        )
    ).all()
    
    deleted_count = 0
    for room in rooms_to_delete:
        db.query(ChatMessage).filter(ChatMessage.chat_room_id == room.id).delete()
        db.delete(room)
        deleted_count += 1
    
    db.commit()
    return {"message": f"Deleted {deleted_count} ended event chat rooms"}





# Direct Messages
@router.post("/direct-messages/", response_model=DirectMessageSchema)
async def send_direct_message(
    dm: DirectMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: str = Depends(get_tenant_context)
):
    """Send direct message to any user"""
    print(f"DEBUG: Direct message - Current user: {current_user.email}")
    print(f"DEBUG: Direct message - Current user tenant_id: {current_user.tenant_id}")
    print(f"DEBUG: Direct message - Tenant context: {tenant_context}")
    print(f"DEBUG: Direct message - Request data: {dm.dict()}")
    
    # Ensure tenant_context is not None
    if not tenant_context:
        print(f"ERROR: Direct message - tenant_context is None or empty")
        print(f"ERROR: Direct message - current_user.tenant_id: {current_user.tenant_id}")
        print(f"ERROR: Direct message - current_user.role: {current_user.role}")
        raise HTTPException(status_code=400, detail="No tenant context available")
    
    # Verify recipient exists - allow cross-tenant messaging
    recipient = db.query(User).filter(
        and_(
            User.email == dm.recipient_email,
            User.is_active == True
        )
    ).first()
    
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient not found")
    
    # Use tenant_context which properly extracts from X-Tenant-ID header
    db_dm = DirectMessage(
        sender_email=current_user.email,
        sender_name=current_user.full_name or current_user.email,
        recipient_email=dm.recipient_email,
        recipient_name=recipient.full_name or recipient.email,
        message=dm.message,
        tenant_id=tenant_context
    )
    
    print(f"DEBUG: Direct message - Creating DB record with tenant_id: {tenant_context}")
    db.add(db_dm)
    db.commit()
    db.refresh(db_dm)
    
    # Send real-time notification to recipient
    await notification_manager.send_user_notification({
        "type": "chat_message",
        "data": {
            "sender_name": current_user.full_name or current_user.email,
            "message": dm.message,
            "timestamp": str(db_dm.created_at)
        }
    }, dm.recipient_email)
    
    # Send in-app notification to recipient
    try:
        from app.crud.notification import notification
        
        print(f"CHAT: Creating direct message notification for {recipient.email}")
        try:
            created_notification = notification.create_user_notification(
                db=db,
                user_id=recipient.id,
                title=f"New direct message from {current_user.full_name or current_user.email}",
                message=f"{dm.message[:100]}{'...' if len(dm.message) > 100 else ''}",
                tenant_id=recipient.tenant_id,
                notification_type="CHAT_MESSAGE",
                priority="LOW",
                send_email=False,
                send_push=False,
                action_url=f"/tenant/{recipient.tenant_id}/chat",
                triggered_by=current_user.email
            )
            print(f"CHAT: Created direct message notification ID {created_notification.id}")
        except Exception as dm_error:
            print(f"CHAT ERROR: Failed to create direct message notification: {dm_error}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"CHAT ERROR: Failed to create direct message notification: {e}")
        import traceback
        traceback.print_exc()
        # Rollback the session to prevent transaction issues
        try:
            db.rollback()
        except Exception as rollback_error:
            print(f"CHAT ERROR: Failed to rollback session: {rollback_error}")
    
    return db_dm

@router.get("/direct-messages/", response_model=List[DirectMessageSchema])
def get_direct_messages(
    with_user: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get direct messages (sent or received) - allow cross-tenant messaging"""
    query = db.query(DirectMessage).filter(
        or_(
            DirectMessage.sender_email == current_user.email,
            DirectMessage.recipient_email == current_user.email
        )
    )
    
    if with_user:
        query = query.filter(
            or_(
                and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == with_user),
                and_(DirectMessage.sender_email == with_user, DirectMessage.recipient_email == current_user.email)
            )
        )
    
    return query.order_by(desc(DirectMessage.created_at)).all()

@router.get("/conversations/")
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users with whom current user has conversations"""
    print(f"DEBUG CONV: Getting conversations for user {current_user.email}")
    
    # Get unique conversation partners - allow cross-tenant conversations
    sent_to = db.query(DirectMessage.recipient_email, DirectMessage.recipient_name).filter(
        DirectMessage.sender_email == current_user.email
    ).distinct()
    
    received_from = db.query(DirectMessage.sender_email, DirectMessage.sender_name).filter(
        DirectMessage.recipient_email == current_user.email
    ).distinct()
    
    conversations = []
    
    # Process sent messages
    for email, name in sent_to:
        if email != current_user.email:
            # Get last message
            last_msg = db.query(DirectMessage).filter(
                or_(
                    and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == email),
                    and_(DirectMessage.sender_email == email, DirectMessage.recipient_email == current_user.email)
                )
            ).order_by(desc(DirectMessage.created_at)).first()
            
            # Count unread messages (only messages FROM other user TO current user)
            unread_count = db.query(DirectMessage).filter(
                and_(
                    DirectMessage.sender_email == email,
                    DirectMessage.recipient_email == current_user.email,
                    DirectMessage.is_read == False
                )
            ).count()
            
            print(f"DEBUG CONV: Sent to {email}, unread_count: {unread_count}, last_msg: {last_msg.message if last_msg else None}")
            
            conversations.append({
                "email": email,
                "name": name,
                "last_message": last_msg.message if last_msg else None,
                "last_message_time": last_msg.created_at if last_msg else None,
                "unread_count": unread_count
            })
    
    # Process received messages
    for email, name in received_from:
        if email != current_user.email and not any(c["email"] == email for c in conversations):
            # Get last message
            last_msg = db.query(DirectMessage).filter(
                or_(
                    and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == email),
                    and_(DirectMessage.sender_email == email, DirectMessage.recipient_email == current_user.email)
                )
            ).order_by(desc(DirectMessage.created_at)).first()
            
            # Count unread messages (only messages FROM other user TO current user)
            unread_count = db.query(DirectMessage).filter(
                and_(
                    DirectMessage.sender_email == email,
                    DirectMessage.recipient_email == current_user.email,
                    DirectMessage.is_read == False
                )
            ).count()
            
            print(f"DEBUG CONV: Received from {email}, unread_count: {unread_count}, last_msg: {last_msg.message if last_msg else None}")
            
            conversations.append({
                "email": email,
                "name": name,
                "last_message": last_msg.message if last_msg else None,
                "last_message_time": last_msg.created_at if last_msg else None,
                "unread_count": unread_count
            })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x["last_message_time"] or datetime.min, reverse=True)
    
    print(f"DEBUG CONV: Returning {len(conversations)} conversations")
    for conv in conversations:
        print(f"DEBUG CONV: {conv['email']} - unread: {conv['unread_count']}, last: {conv['last_message']}")
    
    return conversations

@router.put("/direct-messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark direct message as read"""
    message = db.query(DirectMessage).filter(
        and_(
            DirectMessage.id == message_id,
            DirectMessage.recipient_email == current_user.email
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    return {"message": "Marked as read"}

@router.get("/users/", response_model=List[dict])
def get_available_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all users for direct messaging - no tenant filtering"""
    users = db.query(User).filter(
        and_(
            User.is_active == True,
            User.email != current_user.email
        )
    ).all()
    
    print(f"DEBUG: Found {len(users)} total active users (no tenant filter)")
    print(f"DEBUG: Current user: {current_user.email}, Tenant: {current_user.tenant_id}")
    for user in users:
        print(f"DEBUG: User: {user.email}, Role: {user.role}, Active: {user.is_active}, Tenant: {user.tenant_id}, Full Name: {user.full_name}")
    
    result = [
        {
            "email": user.email,
            "name": user.full_name or user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        for user in users
    ]
    print(f"DEBUG: Returning {len(result)} users as contacts")
    return result

@router.get("/admins/", response_model=List[dict])
def get_available_admins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of admins for direct messaging"""
    admins = db.query(User).filter(
        and_(
            User.tenant_id == current_user.tenant_id,
            or_(
                User.role.in_(["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]),
                User.role.in_(["mt_admin", "hr_admin", "event_admin", "super_admin"])
            ),
            User.is_active == True
        )
    ).all()
    
    return [
        {
            "email": admin.email,
            "name": admin.full_name or admin.email,
            "role": admin.role.value if hasattr(admin.role, 'value') else str(admin.role)
        }
        for admin in admins
    ]

# WebSocket endpoint for real-time notifications
@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
    tenant: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Verify token and get user
        from app.core.security import verify_token
        from app.crud.user import get_by_email
        
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=1008)
            return
        
        user = get_by_email(db, email=payload.get("sub"))
        if not user:
            await websocket.close(code=1008)
            return
        
        await notification_manager.connect_user(websocket, user.email, tenant)
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    
    except WebSocketDisconnect:
        notification_manager.disconnect_user(websocket, user.email if 'user' in locals() else None)
    except Exception as e:
        print(f"WebSocket notification error: {e}")
        await websocket.close(code=1011)

# WebSocket endpoint for real-time chat
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    try:
        # Verify token and get user (simplified - you may want to use proper JWT verification)
        from app.core.security import verify_token
        from app.crud.user import get_by_email
        
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=1008)
            return
        
        user = get_by_email(db, email=payload.get("sub"))
        if not user:
            await websocket.close(code=1008)
            return
        
        # Verify room exists
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            await websocket.close(code=1008)
            return
        
        user_info = {
            "email": user.email,
            "name": user.full_name or user.email,
            "is_admin": (user.role.value if hasattr(user.role, 'value') else str(user.role)).upper() in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]
        }
        
        await manager.connect(websocket, room_id, user_info)
        
        # Notify room about new user
        await manager.broadcast_to_room({
            "type": "user_joined",
            "user": user_info,
            "timestamp": str(datetime.now())
        }, room_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            print(f"🔌 WebSocket received: {message_data['type']} from {user.email} in room {room_id}")
            
            if message_data["type"] == "message":
                print(f"💬 WebSocket message: '{message_data['message'][:50]}...' from {user.email}")
                
                # Save message to database
                db_message = ChatMessage(
                    chat_room_id=room_id,
                    sender_email=user.email,
                    sender_name=user.full_name or user.email,
                    message=message_data["message"],
                    is_admin_message=user_info["is_admin"]
                )
                db.add(db_message)
                db.commit()
                db.refresh(db_message)
                
                print(f"💾 Saved WebSocket message to DB with ID {db_message.id}")
                
                # Broadcast to room
                broadcast_data = {
                    "type": "message",
                    "id": db_message.id,
                    "sender_email": user.email,
                    "sender_name": user.full_name or user.email,
                    "message": message_data["message"],
                    "is_admin_message": user_info["is_admin"],
                    "timestamp": str(db_message.created_at)
                }
                
                await manager.broadcast_to_room(broadcast_data, room_id)
                print(f"📡 Broadcasted WebSocket message to room {room_id}")
                
            elif message_data["type"] == "ping":
                print(f"🏓 WebSocket ping from {user.email}")
                await websocket.send_text(json.dumps({"type": "pong"}))
                print(f"🏓 WebSocket pong sent to {user.email}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast_to_room({
            "type": "user_left",
            "user": user_info,
            "timestamp": str(datetime.now())
        }, room_id)
    except Exception as e:
        await websocket.close(code=1011)