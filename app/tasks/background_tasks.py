import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.participant_cleanup_service import ParticipantCleanupService
from app.tasks.vetting_cleanup import cleanup_expired_vetting_roles

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
        
        # Start vetting committee cleanup task
        asyncio.create_task(self._vetting_cleanup_task())
    
    async def stop_background_tasks(self):
        """Stop all background tasks"""
        self.running = False
        logger.info("Stopping background tasks...")
    
    async def _participant_cleanup_task(self):
        """Background task to clean up expired participants"""
        while self.running:
            try:
                db: Session = SessionLocal()
                try:
                    deleted_count = ParticipantCleanupService.cleanup_expired_participants(db)
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired participants")
                finally:
                    db.close()
                
                # Run every 24 hours
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"Error in participant cleanup task: {str(e)}")
                await asyncio.sleep(86400)  # Wait 24 hours before retrying
    
    async def _vetting_cleanup_task(self):
        """Background task to revoke expired vetting committee roles"""
        while self.running:
            try:
                cleanup_expired_vetting_roles()
                
                # Run every 24 hours
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"Error in vetting cleanup task: {str(e)}")
                await asyncio.sleep(86400)  # Wait 24 hours before retrying

# Global instance
background_task_manager = BackgroundTaskManager()
