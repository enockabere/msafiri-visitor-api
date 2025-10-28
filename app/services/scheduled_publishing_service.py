from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.news_update import NewsUpdate
from app.core.notifications import send_news_notification
from app.db.database import get_db
import asyncio
import logging

logger = logging.getLogger(__name__)

class ScheduledPublishingService:
    @staticmethod
    async def check_and_publish_scheduled_news():
        """Check for news items that should be published now and publish them"""
        try:
            db = next(get_db())
            current_time = datetime.now(timezone.utc)
            
            # Find news items that are scheduled to be published now or in the past
            scheduled_news = db.query(NewsUpdate).filter(
                NewsUpdate.is_published == False,
                NewsUpdate.scheduled_publish_at <= current_time,
                NewsUpdate.scheduled_publish_at.isnot(None)
            ).all()
            
            for news in scheduled_news:
                # Publish the news
                news.is_published = True
                news.published_at = current_time
                news.scheduled_publish_at = None  # Clear the scheduled time
                
                # Send notification
                try:
                    await send_news_notification(news, db)
                    logger.info(f"Published scheduled news: {news.title} (ID: {news.id})")
                except Exception as e:
                    logger.error(f"Failed to send notification for news {news.id}: {e}")
            
            db.commit()
            
            if scheduled_news:
                logger.info(f"Published {len(scheduled_news)} scheduled news items")
                
        except Exception as e:
            logger.error(f"Error in scheduled publishing service: {e}")
            db.rollback()
        finally:
            db.close()

async def send_news_notification(news: NewsUpdate, db: Session):
    """Send push notification for published news"""
    from app.services.notification_service import NotificationService
    
    notification_service = NotificationService()
    
    # Create notification message
    title = "📰 New Update"
    if news.is_important:
        title = "🚨 Important Update"
    
    body = f"{news.title}\n{news.summary[:100]}..."
    
    # Send to all users in the tenant
    await notification_service.send_tenant_notification(
        tenant_id=news.tenant_id,
        title=title,
        body=body,
        data={
            "type": "news_update",
            "news_id": str(news.id),
            "category": news.category
        }
    )