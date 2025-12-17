#!/usr/bin/env python3
"""
Manual script to check vetting committee deadlines
Run this daily via cron job or task scheduler
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.vetting_notification_service import check_deadline_notifications

if __name__ == "__main__":
    print("Checking vetting committee deadlines...")
    check_deadline_notifications()
    print("Deadline check completed.")