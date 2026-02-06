# File: app/tasks/vetting_scheduler.py
from celery import Celery
from datetime import datetime, timedelta
from app.services.vetting_notification_service import check_deadline_notifications

# Initialize Celery (you may need to configure this based on your setup)
celery_app = Celery('vetting_scheduler')

@celery_app.task
def check_vetting_deadlines():
    """Scheduled task to check for approaching deadlines"""
    check_deadline_notifications()

# Schedule the task to run daily
celery_app.conf.beat_schedule = {
    'check-vetting-deadlines': {
        'task': 'app.tasks.vetting_scheduler.check_vetting_deadlines',
        'schedule': 86400.0,  # Run every 24 hours
    },
}

celery_app.conf.timezone = 'UTC'
