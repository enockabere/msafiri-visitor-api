# File: app/core/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def start_scheduler():
    """Start all scheduled jobs"""
    from app.services.vetting_deadline_scheduler import (
        check_and_send_deadline_reminders,
        check_and_remove_expired_roles
    )

    try:
        # Check for deadline reminders every hour
        scheduler.add_job(
            check_and_send_deadline_reminders,
            trigger=IntervalTrigger(hours=1),
            id='vetting_deadline_reminders',
            name='Check and send vetting deadline reminders',
            replace_existing=True
        )

        # Check for expired roles every hour
        scheduler.add_job(
            check_and_remove_expired_roles,
            trigger=IntervalTrigger(hours=1),
            id='vetting_role_removal',
            name='Remove expired vetting roles',
            replace_existing=True
        )

        scheduler.start()
        logger.info("✅ Scheduler started successfully")
        logger.info(f"Active jobs: {len(scheduler.get_jobs())}")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

def stop_scheduler():
    """Stop scheduler gracefully"""
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
