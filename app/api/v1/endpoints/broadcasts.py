from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime
from app.db.database import get_db
from app.models.broadcast import Broadcast, BroadcastRead, BroadcastType, Priority
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/")
def create_broadcast(
    broadcast_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates broadcast for all tenant users"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    broadcast = Broadcast(
        title=broadcast_data["title"],
        content=broadcast_data["content"],
        broadcast_type=BroadcastType(broadcast_data.get("broadcast_type", "news")),
        priority=Priority(broadcast_data.get("priority", "normal")),
        tenant_id=current_user.tenant_id,
        created_by=current_user.email,
        expires_at=datetime.fromisoformat(broadcast_data["expires_at"]) if broadcast_data.get("expires_at") else None
    )
    
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    
    # Queue notifications for all tenant users
    from app.core.notifications import queue_notification
    from app.models.visitor_enhancements import NotificationType
    
    # Get all active users in tenant
    tenant_users = db.query(User).filter(
        and_(
            User.tenant_id == current_user.tenant_id,
            User.is_active == True
        )
    ).all()
    
    # Send notification to each user
    for user in tenant_users:
        queue_notification(
            recipient_email=user.email,
            notification_type=NotificationType.EVENT_REMINDER,  # Reusing existing type
            title=f"📢 {broadcast.title}",
            message=broadcast.content[:200] + "..." if len(broadcast.content) > 200 else broadcast.content,
            data={
                "broadcast_id": broadcast.id,
                "broadcast_type": broadcast.broadcast_type.value,
                "priority": broadcast.priority.value
            }
        )
    
    return {
        "id": broadcast.id,
        "title": broadcast.title,
        "content": broadcast.content,
        "broadcast_type": broadcast.broadcast_type.value,
        "priority": broadcast.priority.value,
        "created_at": broadcast.created_at,
        "expires_at": broadcast.expires_at,
        "recipients_notified": len(tenant_users)
    }

@router.get("/")
def get_broadcasts(
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all broadcasts for current user's tenant"""
    
    query = db.query(Broadcast).filter(
        and_(
            Broadcast.tenant_id == current_user.tenant_id,
            Broadcast.is_active == True
        )
    )
    
    if not include_expired:
        query = query.filter(
            or_(
                Broadcast.expires_at.is_(None),
                Broadcast.expires_at > datetime.now()
            )
        )
    
    broadcasts = query.order_by(
        Broadcast.priority.desc(),
        desc(Broadcast.created_at)
    ).all()
    
    # Get read status for current user
    read_broadcasts = db.query(BroadcastRead.broadcast_id).filter(
        BroadcastRead.user_email == current_user.email
    ).all()
    read_ids = {r[0] for r in read_broadcasts}
    
    result = []
    for broadcast in broadcasts:
        result.append({
            "id": broadcast.id,
            "title": broadcast.title,
            "content": broadcast.content,
            "broadcast_type": broadcast.broadcast_type.value,
            "priority": broadcast.priority.value,
            "created_by": broadcast.created_by,
            "created_at": broadcast.created_at,
            "expires_at": broadcast.expires_at,
            "is_read": broadcast.id in read_ids,
            "is_expired": broadcast.expires_at and broadcast.expires_at < datetime.now()
        })
    
    return result

@router.post("/{broadcast_id}/read")
def mark_broadcast_read(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark broadcast as read by current user"""
    
    # Check if broadcast exists and belongs to user's tenant
    broadcast = db.query(Broadcast).filter(
        and_(
            Broadcast.id == broadcast_id,
            Broadcast.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # Check if already read
    existing_read = db.query(BroadcastRead).filter(
        and_(
            BroadcastRead.broadcast_id == broadcast_id,
            BroadcastRead.user_email == current_user.email
        )
    ).first()
    
    if existing_read:
        return {"message": "Already marked as read"}
    
    # Mark as read
    read_record = BroadcastRead(
        broadcast_id=broadcast_id,
        user_email=current_user.email,
        read_at=datetime.now()
    )
    
    db.add(read_record)
    db.commit()
    
    return {"message": "Marked as read"}

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread broadcasts for current user"""
    
    # Get all active, non-expired broadcasts for tenant
    active_broadcasts = db.query(Broadcast.id).filter(
        and_(
            Broadcast.tenant_id == current_user.tenant_id,
            Broadcast.is_active == True,
            or_(
                Broadcast.expires_at.is_(None),
                Broadcast.expires_at > datetime.now()
            )
        )
    ).subquery()
    
    # Get read broadcasts for user
    read_broadcasts = db.query(BroadcastRead.broadcast_id).filter(
        BroadcastRead.user_email == current_user.email
    ).subquery()
    
    # Count unread
    unread_count = db.query(active_broadcasts.c.id).outerjoin(
        read_broadcasts, active_broadcasts.c.id == read_broadcasts.c.broadcast_id
    ).filter(read_broadcasts.c.broadcast_id.is_(None)).count()
    
    return {"unread_count": unread_count}

@router.get("/admin/stats/{broadcast_id}")
def get_broadcast_stats(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets broadcast read statistics"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    broadcast = db.query(Broadcast).filter(
        and_(
            Broadcast.id == broadcast_id,
            Broadcast.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # Get total tenant users
    total_users = db.query(User).filter(
        and_(
            User.tenant_id == current_user.tenant_id,
            User.is_active == True
        )
    ).count()
    
    # Get read count
    read_count = db.query(BroadcastRead).filter(
        BroadcastRead.broadcast_id == broadcast_id
    ).count()
    
    # Get read percentage
    read_percentage = (read_count / total_users * 100) if total_users > 0 else 0
    
    return {
        "broadcast_id": broadcast_id,
        "title": broadcast.title,
        "total_recipients": total_users,
        "read_count": read_count,
        "unread_count": total_users - read_count,
        "read_percentage": round(read_percentage, 2),
        "created_at": broadcast.created_at,
        "expires_at": broadcast.expires_at
    }

@router.put("/{broadcast_id}")
def update_broadcast(
    broadcast_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin updates broadcast"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    broadcast = db.query(Broadcast).filter(
        and_(
            Broadcast.id == broadcast_id,
            Broadcast.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # Update fields
    for field, value in update_data.items():
        if field in ["title", "content"]:
            setattr(broadcast, field, value)
        elif field == "expires_at" and value:
            broadcast.expires_at = datetime.fromisoformat(value)
        elif field == "is_active":
            broadcast.is_active = value
    
    db.commit()
    db.refresh(broadcast)
    
    return {
        "id": broadcast.id,
        "title": broadcast.title,
        "content": broadcast.content,
        "is_active": broadcast.is_active,
        "expires_at": broadcast.expires_at
    }

@router.delete("/{broadcast_id}")
def delete_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin deactivates broadcast"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    broadcast = db.query(Broadcast).filter(
        and_(
            Broadcast.id == broadcast_id,
            Broadcast.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    broadcast.is_active = False
    db.commit()
    
    return {"message": "Broadcast deactivated"}
