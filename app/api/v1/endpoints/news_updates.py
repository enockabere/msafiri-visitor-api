from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
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

def _get_tenant_numeric_id(db: Session, tenant_slug: str) -> int:
    """Get numeric tenant ID from slug"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid tenant")
    return tenant.id

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
    
    tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
    
    news_update = crud_news_update.create_news_update(
        db=db,
        news_update=news_update_in,
        tenant_id=tenant_numeric_id,
        created_by=current_user.email
    )
    
    # Send notifications if published immediately
    if news_update.is_published:
        _send_news_notifications(db, news_update, tenant_numeric_id)
    
    logger.info(f"News update created: {news_update.id} by {current_user.email}")
    return news_update

@router.get("/", response_model=NewsUpdateListResponse)
def get_news_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    published_only: bool = Query(False),
    search: str = Query(None, description="Search in title, summary, and content")
):
    """Get news updates for current tenant"""
    try:
        logger.info(f"Getting news updates for user: {current_user.email}")
        
        if not current_user.tenant_id:
            raise HTTPException(status_code=400, detail="User must belong to a tenant")
        
        tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
        logger.info(f"Tenant slug: {current_user.tenant_id}, Numeric ID: {tenant_numeric_id}")
        
        news_updates = crud_news_update.get_news_updates(
            db=db,
            tenant_id=tenant_numeric_id,
            skip=skip,
            limit=limit,
            published_only=published_only,
            search=search
        )
        
        total = crud_news_update.get_news_updates_count(
            db=db,
            tenant_id=tenant_numeric_id,
            published_only=published_only,
            search=search
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
    
    tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
    
    news_update = crud_news_update.get_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=tenant_numeric_id
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
    
    tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
    
    # Get original state
    original_news = crud_news_update.get_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=tenant_numeric_id
    )
    
    news_update = crud_news_update.update_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=tenant_numeric_id,
        news_update_update=news_update_in
    )
    
    if not news_update:
        raise HTTPException(status_code=404, detail="News update not found")
    
    # Send notifications every time news is published (including republishing)
    if news_update.is_published:
        _send_news_notifications(db, news_update, tenant_numeric_id)
    
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
    
    tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
    
    news_update = crud_news_update.publish_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=tenant_numeric_id,
        is_published=publish_data.is_published
    )
    
    if not news_update:
        raise HTTPException(status_code=404, detail="News update not found")
    
    # Send push notifications every time publishing (including republishing)
    if publish_data.is_published:
        _send_news_notifications(db, news_update, tenant_numeric_id)
    
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
    
    tenant_numeric_id = _get_tenant_numeric_id(db, current_user.tenant_id)
    
    success = crud_news_update.delete_news_update(
        db=db,
        news_update_id=news_update_id,
        tenant_id=tenant_numeric_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="News update not found")
    
    logger.info(f"News update deleted: {news_update_id} by {current_user.email}")
    return {"message": "News update deleted successfully"}

# Mobile app endpoint - Get news from all tenants
@router.get("/mobile/published", response_model=List[NewsUpdateResponse])
def get_published_news_for_mobile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Get published news updates for mobile app from all tenants"""
    try:
        logger.info(f"📱 Mobile news request from user: {current_user.email}")
        logger.info(f"📱 User tenant_id: {current_user.tenant_id}")
        
        # Get news from all tenants for mobile users
        news_updates = crud_news_update.get_all_published_news_for_mobile(
            db=db,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"📱 Mobile news found: {len(news_updates)} items across all tenants")
        for news in news_updates:
            logger.info(f"📱   - News {news.id}: '{news.title}' (tenant: {news.tenant_id}, published: {news.is_published}, expires: {news.expires_at})")
        
        return news_updates
    except Exception as e:
        logger.error(f"📱 Error in mobile news endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def _send_news_notifications(db: Session, news_update, tenant_id: int):
    """Send push notifications for published news"""
    try:
        logger.info(f"🔔 Starting notification process for news update: {news_update.id}")
        
        # Get tenant slug from numeric ID
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            logger.error(f"🔔 Tenant not found for ID: {tenant_id}")
            return
        
        logger.info(f"🔔 Found tenant: {tenant.slug}")
        
        # Get all active users across all tenants for push notifications
        tenant_users = db.query(UserModel).filter(
            UserModel.is_active == True
        ).all()
        
        logger.info(f"🔔 Found {len(tenant_users)} active users across all tenants")
        
        notification_title = f"📰 {news_update.title}"
        if news_update.is_important:
            notification_title = f"🚨 {news_update.title}"
        
        notification_body = news_update.summary[:100] + "..." if len(news_update.summary) > 100 else news_update.summary
        
        notifications_sent = 0
        users_with_tokens = 0
        
        for user in tenant_users:
            try:
                if user.fcm_token:
                    users_with_tokens += 1
                    logger.info(f"🔔 Sending notification to {user.email} (has FCM token)")
                else:
                    logger.info(f"🔔 Skipping {user.email} (no FCM token)")
                    continue
                
                success = firebase_service.send_to_user(
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
                
                if success:
                    notifications_sent += 1
                    
            except Exception as e:
                logger.error(f"🔔 Failed to send push notification to {user.email}: {str(e)}")
        
        logger.info(f"🔔 Notification summary for news {news_update.id}: {notifications_sent}/{users_with_tokens} sent successfully (out of {len(tenant_users)} total users)")
        
    except Exception as e:
        logger.error(f"🔔 Failed to send push notifications for news update {news_update.id}: {str(e)}")