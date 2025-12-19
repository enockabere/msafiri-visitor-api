# File: app/services/vetting_deadline_scheduler.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.vetting_committee import VettingCommittee, VettingStatus
from app.models.vetting_email_template import VettingEmailTemplate
from app.models.event import Event
from app.models.vetting_role_assignment import VettingRoleAssignment
from app.models.vetting_deadline_reminder import VettingDeadlineReminder
from app.core.email_service import email_service
from app.crud.vetting_committee import remove_vetting_roles_after_deadline
from app.db.database import SessionLocal
import logging
import os

logger = logging.getLogger(__name__)

def get_portal_url():
    """Get portal URL from environment"""
    return os.getenv('FRONTEND_URL', os.getenv('PORTAL_URL', 'http://localhost:3000'))

def check_and_send_deadline_reminders():
    """Run every hour to check for committees needing deadline reminders"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        two_days_from_now = now + timedelta(days=2)
        three_days_from_now = now + timedelta(days=3)  # Give 1 day window

        # Find committees with deadline in 2 days that haven't been reminded
        # Only send reminders for OPEN vetting committees
        committees = db.query(VettingCommittee).filter(
            VettingCommittee.selection_end_date >= two_days_from_now,
            VettingCommittee.selection_end_date <= three_days_from_now,
            VettingCommittee.status == VettingStatus.OPEN,
            VettingCommittee.reminders_sent == False
        ).all()

        logger.info(f"Found {len(committees)} committees needing deadline reminders")

        for committee in committees:
            try:
                send_deadline_reminder(committee, db)
            except Exception as e:
                logger.error(f"Failed to send reminder for committee {committee.id}: {e}")

    except Exception as e:
        logger.error(f"Error in deadline reminder job: {e}")
    finally:
        db.close()

def send_deadline_reminder(committee: VettingCommittee, db: Session):
    """Send deadline reminder to committee and approver"""

    # Check if already sent
    existing = db.query(VettingDeadlineReminder).filter(
        VettingDeadlineReminder.committee_id == committee.id,
        VettingDeadlineReminder.reminder_type == "two_day_warning"
    ).first()

    if existing:
        logger.info(f"Reminder already sent for committee {committee.id}")
        return

    event = db.query(Event).filter(Event.id == committee.event_id).first()
    if not event:
        logger.error(f"Event not found for committee {committee.id}")
        return

    recipients_count = 0
    portal_url = get_portal_url()

    # Send to committee members
    for member in committee.members:
        subject = f"⏰ Deadline Reminder: Vetting for {event.title}"
        message = f"""Dear {member.full_name},

This is a reminder that the vetting deadline for {event.title} is approaching in 2 days.

Deadline: {committee.selection_end_date.strftime('%B %d, %Y at %H:%M UTC')}

Please complete your participant selections before the deadline.
After the deadline, you will lose access to the vetting interface.

Login to continue: {portal_url}/vetting

Best regards,
MSF Msafiri Team"""

        try:
            email_service.send_notification_email(
                to_email=member.email,
                user_name=member.full_name,
                title=subject,
                message=message
            )
            recipients_count += 1
            logger.info(f"Sent deadline reminder to {member.email}")
        except Exception as e:
            logger.error(f"Failed to send reminder to {member.email}: {e}")

    # Send to approver
    if committee.approver:
        subject = f"⏰ Deadline Reminder: Approval Needed for {event.title}"
        message = f"""Dear {committee.approver.full_name or 'Approver'},

This is a reminder that the vetting deadline for {event.title} is approaching in 2 days.

Deadline: {committee.selection_end_date.strftime('%B %d, %Y at %H:%M UTC')}

Please ensure that the committee completes their selections and you review them before the deadline.

Login to review: {portal_url}/tenant/{committee.tenant_id}/events/{event.id}/vetting

Best regards,
MSF Msafiri Team"""

        try:
            email_service.send_notification_email(
                to_email=committee.approver_email,
                user_name=committee.approver.full_name if committee.approver else "Approver",
                title=subject,
                message=message
            )
            recipients_count += 1
            logger.info(f"Sent deadline reminder to approver {committee.approver_email}")
        except Exception as e:
            logger.error(f"Failed to send reminder to approver {committee.approver_email}: {e}")

    # Record reminder sent
    reminder = VettingDeadlineReminder(
        committee_id=committee.id,
        reminder_type="two_day_warning",
        recipients_count=recipients_count
    )
    db.add(reminder)

    committee.reminders_sent = True
    db.commit()

    logger.info(f"✅ Sent deadline reminders for committee {committee.id} to {recipients_count} recipients")

def check_and_remove_expired_roles():
    """Run every hour to remove vetting roles after deadline"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find committees past deadline with active role assignments
        expired_committees = db.query(VettingCommittee).filter(
            VettingCommittee.selection_end_date < now
        ).all()

        logger.info(f"Checking {len(expired_committees)} committees for expired roles")

        for committee in expired_committees:
            # Check if there are active assignments
            active_assignments = db.query(VettingRoleAssignment).filter(
                VettingRoleAssignment.committee_id == committee.id,
                VettingRoleAssignment.is_active == True
            ).count()

            if active_assignments > 0:
                try:
                    removed_count = remove_vetting_roles_after_deadline(db, committee.id)
                    logger.info(f"✅ Removed {removed_count} role assignments for expired committee {committee.id}")
                except Exception as e:
                    logger.error(f"Failed to remove roles for committee {committee.id}: {e}")

    except Exception as e:
        logger.error(f"Error in role removal job: {e}")
    finally:
        db.close()
