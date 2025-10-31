import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.agenda_notification_service import send_agenda_start_notifications

logger = logging.getLogger(__name__)

class AgendaNotificationScheduler:
    def __init__(self):
        self.running = False
        
    async def start(self):
        """Start the agenda notification scheduler"""
        self.running = True
        logger.info("Starting agenda notification scheduler")
        
        while self.running:
            try:
                # Check every minute for upcoming agenda items
                db = SessionLocal()
                try:
                    send_agenda_start_notifications(db)
                finally:
                    db.close()
                    
                # Wait 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in agenda scheduler: {str(e)}")
                await asyncio.sleep(60)  # Continue after error
                
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Stopping agenda notification scheduler")

# Global scheduler instance
agenda_scheduler = AgendaNotificationScheduler()