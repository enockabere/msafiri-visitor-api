"""
Scheduled task to publish certificates and send email notifications
Run this as a cron job or scheduled task every hour
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.event_certificate import EventCertificate, ParticipantCertificate
from app.models.event_participant import EventParticipant
from app.models.user import User
from app.core.email_service import email_service
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def publish_due_certificates():
    """
    Check for certificates whose certificate_date has been reached
    and publish them + send email notifications
    """
    db: Session = SessionLocal()
    
    try:
        now = datetime.now(timezone.utc)
        logger.info(f"[CERT SCHEDULER] Running certificate publisher at {now}")
        
        # Find all unpublished certificates whose date has been reached
        due_certificates = db.query(EventCertificate).filter(
            EventCertificate.is_published == False,
            EventCertificate.certificate_date <= now,
            EventCertificate.certificate_date.isnot(None)
        ).all()
        
        logger.info(f"[CERT SCHEDULER] Found {len(due_certificates)} certificates ready to publish")
        
        for event_cert in due_certificates:
            try:
                # Get all participant certificates for this event certificate
                participant_certs = db.query(ParticipantCertificate).filter(
                    ParticipantCertificate.event_certificate_id == event_cert.id,
                    ParticipantCertificate.email_sent == False
                ).all()
                
                logger.info(f"[CERT SCHEDULER] Publishing certificate {event_cert.id} for {len(participant_certs)} participants")
                
                # Publish the certificate
                event_cert.is_published = True
                
                # Send email to each participant
                emails_sent = 0
                for participant_cert in participant_certs:
                    try:
                        # Get participant details
                        participant = db.query(EventParticipant).filter(
                            EventParticipant.id == participant_cert.participant_id
                        ).first()
                        
                        if not participant or not participant.user_id:
                            logger.warning(f"[CERT SCHEDULER] Participant {participant_cert.participant_id} not found or has no user")
                            continue
                        
                        # Get user email
                        user = db.query(User).filter(User.id == participant.user_id).first()
                        if not user or not user.email:
                            logger.warning(f"[CERT SCHEDULER] User not found or has no email for participant {participant_cert.participant_id}")
                            continue
                        
                        # Send email notification
                        try:
                            # Build certificate URL
                            api_url = os.getenv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
                            cert_url = f"{api_url}/api/v1/events/{event_cert.event_id}/certificates/{event_cert.id}/generate/{participant.id}"
                            
                            email_service.send_certificate_notification_email(
                                to_email=user.email,
                                participant_name=participant.full_name,
                                event_title=event_cert.event.title if event_cert.event else "Event",
                                certificate_url=cert_url
                            )
                            
                            # Mark email as sent
                            participant_cert.email_sent = True
                            participant_cert.email_sent_at = datetime.now(timezone.utc)
                            emails_sent += 1
                            
                            logger.info(f"[CERT SCHEDULER] Email sent to {user.email} for participant {participant.id}")
                        except Exception as email_error:
                            logger.error(f"[CERT SCHEDULER] Failed to send email to {user.email}: {email_error}")
                            # Continue with other participants even if one email fails
                            continue
                    
                    except Exception as participant_error:
                        logger.error(f"[CERT SCHEDULER] Error processing participant {participant_cert.participant_id}: {participant_error}")
                        continue
                
                db.commit()
                logger.info(f"[CERT SCHEDULER] Successfully published certificate {event_cert.id} and sent {emails_sent} emails")
                
            except Exception as cert_error:
                logger.error(f"[CERT SCHEDULER] Error processing certificate {event_cert.id}: {cert_error}")
                db.rollback()
                continue
        
        logger.info(f"[CERT SCHEDULER] Certificate publisher completed")
        
    except Exception as e:
        logger.error(f"[CERT SCHEDULER] Fatal error in certificate publisher: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    publish_due_certificates()
