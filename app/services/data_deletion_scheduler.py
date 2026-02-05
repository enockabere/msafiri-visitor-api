import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.data_deletion_service import DataDeletionService

logger = logging.getLogger(__name__)

class DataDeletionScheduler:
    """Scheduler for automatic data deletion tasks"""
    
    @staticmethod
    async def run_daily_cleanup():
        """Run daily data deletion cleanup"""
        logger.info("Starting daily data deletion cleanup")
        
        db = SessionLocal()
        try:
            results = DataDeletionService.process_automatic_deletions(db)
            
            logger.info(f"Daily cleanup completed: {results['immediate_deletions']} immediate deletions, {results['monthly_deletions']} monthly deletions")
            
            if results['errors']:
                logger.error(f"Errors during cleanup: {results['errors']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    async def schedule_cleanup_task():
        """Schedule the cleanup task to run daily at 2 AM"""
        while True:
            try:
                now = datetime.now()
                # Calculate next 2 AM
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if now >= next_run:
                    next_run += timedelta(days=1)
                
                # Wait until next run time
                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Next data deletion cleanup scheduled for {next_run}")
                
                await asyncio.sleep(wait_seconds)
                
                # Run the cleanup
                await DataDeletionScheduler.run_daily_cleanup()
                
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)

# Function to start the scheduler
def start_data_deletion_scheduler():
    """Start the data deletion scheduler"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(DataDeletionScheduler.schedule_cleanup_task())
        logger.info("Data deletion scheduler started")
    except Exception as e:
        logger.error(f"Failed to start data deletion scheduler: {e}")