from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.news_update import (
    NewsUpdateCreate, 
    NewsUpdateUpdate, 
    NewsUpdateResponse, 
    NewsUpdateListResponse,
    NewsUpdatePublish
)
from app.crud import news_update as crud_news_update
from app.services.firebase_service import firebase_service
from app.models.user import User as UserModel
import logging
import math

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=NewsUpdateResponse)
def create_news_update(
    *,
    db: Session = Depends(get_db),
    news_update_in: NewsUpdateCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new news update"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    news_update = crud_news_update.create_news_update(
        db=db,
        news_update=news_update_in,
        tenant_id=int(current_user.tenant_id),
        created_by=current_user.email
    )
    
    # Send notifications if published immediately
    if news_update.is_published:
        _send_news_notifications(db, news_update, current_user.tenant_id)
    
    logger.info(f"News update created: {news_update.id} by {current_user.email}")
    return news_update

@router.get("/", response_model=NewsUpdateListResponse)
def get_news_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    published_only: bool = Query(False)
):
    """Get news updates for current tenant"""
    try:
        logger.info(f"Getting news updates for user: {current_user.email}")
        
        if not current_user.tenant_id:
            raise HTTPException(status_code=400, detail="User must belong to a tenant")
        
        tenant_id = int(current_user.tenant_id)
        logger.info(f"Tenant ID: {tenant_id}")
        
        news_updates = crud_news_update.get_news_updates(
            db=db,
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            published_only=published_only
        )
        
        total = crud_news_update.get_news_updates_count(
            db=db,
            tenant_id=tenant_id,
            published_only=published_only
        )
        
        pages = math.ceil(total / limit) if total > 0 else 0
        page = (skip // limit) + 1
        
        logger.info(f"Found {len(news_updates)} news updates, total: {total}")
        
        return NewsUpdateListResponse(
            items=news_updates,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Error getting news updates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{news_update_id}", response_model=NewsUpdateResponse)
def get_news_update(
    news_update_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific news update"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    news_update = crud_news_update.get_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=int(current_user.tenant_id)
    )
    
    if not news_update:
        raise HTTPException(status_code=404, detail="News update not found")
    
    return news_update

@router.put("/{news_update_id}", response_model=NewsUpdateResponse)
def update_news_update(
    news_update_id: int,
    news_update_in: NewsUpdateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a news update"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    # Get original state
    original_news = crud_news_update.get_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=int(current_user.tenant_id)
    )
    
    news_update = crud_news_update.update_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=int(current_user.tenant_id),
        news_update_update=news_update_in
    )
    
    if not news_update:
        raise HTTPException(status_code=404, detail="News update not found")
    
    # Send notifications if newly published
    if news_update.is_published and (not original_news or not original_news.is_published):
        _send_news_notifications(db, news_update, current_user.tenant_id)
    
    logger.info(f"News update updated: {news_update_id} by {current_user.email}")
    return news_update

@router.patch("/{news_update_id}/publish", response_model=NewsUpdateResponse)
def publish_news_update(
    news_update_id: int,
    publish_data: NewsUpdatePublish,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Publish or unpublish a news update"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    news_update = crud_news_update.publish_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=int(current_user.tenant_id),
        is_published=publish_data.is_published
    )
    
    if not news_update:
        raise HTTPException(status_code=404, detail="News update not found")
    
    # Send push notifications when publishing
    if publish_data.is_published:
        _send_news_notifications(db, news_update, current_user.tenant_id)
    
    action = "published" if publish_data.is_published else "unpublished"
    logger.info(f"News update {action}: {news_update_id} by {current_user.email}")
    
    return news_update

@router.delete("/{news_update_id}")
def delete_news_update(
    news_update_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a news update"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    success = crud_news_update.delete_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=int(current_user.tenant_id)
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="News update not found")
    
    logger.info(f"News update deleted: {news_update_id} by {current_user.email}")
    return {"message": "News update deleted successfully"}

# Mobile app endpoint
@router.get("/mobile/published", response_model=List[NewsUpdateResponse])
def get_published_news_for_mobile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get published news updates for mobile app"""
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    
    news_updates = crud_news_update.get_published_news_for_mobile(
        db=db,
        tenant_id=int(current_user.tenant_id),
        skip=skip,
        limit=limit
    )
    
    return news_updates

def _send_news_notifications(db: Session, news_update, tenant_id: int):
    """Send push notifications for published news"""
    try:
        # Get all users in the tenant for push notifications
        tenant_users = db.query(UserModel).filter(
            UserModel.tenant_id == tenant_id,
            UserModel.is_active == True
        ).all()
        
        notification_title = f"📰 {news_update.title}"
        if news_update.is_important:
            notification_title = f"🚨 {news_update.title}"
        
        notification_body = news_update.summary[:100] + "..." if len(news_update.summary) > 100 else news_update.summary
        
        for user in tenant_users:
            try:
                firebase_service.send_to_user(
                    db=db,
                    user_email=user.email,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "news_update",
                        "news_id": str(news_update.id),
                        "category": news_update.category.value,
                        "is_important": str(news_update.is_important),
                        "content_type": news_update.content_type
                    }
                )
            except Exception as e:
                logger.error(f"Failed to send push notification to {user.email}: {str(e)}")
        
        logger.info(f"Push notifications sent for news update: {news_update.id}")
        
    except Exception as e:
        logger.error(f"Failed to send push notifications for news update {news_update.id}: {str(e)}")