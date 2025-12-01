import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.participant_cleanup_service import ParticipantCleanupService

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """Manages background tasks for the application"""
    
    def __init__(self):
        self.running = False
    
    async def start_background_tasks(self):
        """Start all background tasks"""
        self.running = True
        logger.info("Starting background tasks...")
        
        # Start participant cleanup task
        asyncio.create_task(self._participant_cleanup_task())
    
    async def stop_background_tasks(self):
        """Stop all background tasks"""
        self.running = False
        logger.info("Stopping background tasks...")
    
    async def _participant_cleanup_task(self):
        """Background task to clean up expired participants"""
        while self.running:
            try:
                logger.info("Running participant cleanup task...")
                
                db: Session = SessionLocal()
                try:
                    deleted_count = ParticipantCleanupService.cleanup_expired_participants(db)
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired participants")
                    else:
                        logger.info("No expired participants to clean up")
                finally:
                    db.close()
                
                # Run every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in participant cleanup task: {str(e)}")
                await asyncio.sleep(3600)  # Wait an hour before retrying

# Global instance
background_task_manager = BackgroundTaskManager()