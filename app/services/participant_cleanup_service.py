from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.core.email_service import email_service
import logging

logger = logging.getLogger(__name__)

class ParticipantCleanupService:
    """Service to handle automatic deletion of participants after 24 hours"""
    
    @staticmethod
    def cleanup_expired_participants(db: Session):
        """Delete participants with not_selected, canceled, or declined status after 24 hours"""
        try:
            # Calculate cutoff time (24 hours ago)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Find participants to delete
            participants_to_delete = db.query(EventParticipant).filter(
                EventParticipant.status.in_(["not_selected", "canceled", "declined"]),
                EventParticipant.updated_at <= cutoff_time
            ).all()
            
            logger.info(f"Found {len(participants_to_delete)} participants to delete")
            
            for participant in participants_to_delete:
                try:
                    # Send final communication before deletion
                    ParticipantCleanupService._send_deletion_notification(participant, db)
                    
                    # Delete participant and all related data
                    ParticipantCleanupService._delete_participant_data(participant, db)
                    
                    logger.info(f"Deleted participant {participant.id} ({participant.email}) with status {participant.status}")
                    
                except Exception as e:
                    logger.error(f"Failed to delete participant {participant.id}: {str(e)}")
                    db.rollback()
                    # Start fresh transaction for next participant
                    db.begin()
                    continue
            
            return len(participants_to_delete)
            
        except Exception as e:
            logger.error(f"Error in cleanup_expired_participants: {str(e)}")
            db.rollback()
            return 0
    
    @staticmethod
    def _send_deletion_notification(participant: EventParticipant, db: Session):
        """Send final notification before data deletion"""
        try:
            if not participant.email or not participant.email.strip():
                return
            
            event = db.query(Event).filter(Event.id == participant.event_id).first()
            if not event:
                return
            
            status_messages = {
                "not_selected": "your application was not selected",
                "canceled": "your registration was canceled", 
                "declined": "you declined participation"
            }
            
            subject = f"Data Deletion Notice - {event.title}"
            message = f"""
            <p>Dear {participant.full_name},</p>
            <p>This is to inform you that since {status_messages.get(participant.status, 'your status was updated')}, 
            your personal data related to <strong>{event.title}</strong> will be permanently deleted from our system 
            in accordance with our data retention policy.</p>
            
            <div style="margin: 20px 0; padding: 20px; background-color: #fef3c7; border-left: 4px solid #f59e0b;">
                <p><strong>Event:</strong> {event.title}</p>
                <p><strong>Your Status:</strong> {participant.status.replace('_', ' ').title()}</p>
                <p><strong>Data Deletion:</strong> Within 24 hours</p>
            </div>
            
            <p>If you have any questions or concerns, please contact us immediately.</p>
            <p>Thank you for your understanding.</p>
            """
            
            email_service.send_notification_email(
                to_email=participant.email,
                user_name=participant.full_name,
                title=subject,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Failed to send deletion notification to {participant.email}: {str(e)}")
    
    @staticmethod
    def _delete_participant_data(participant: EventParticipant, db: Session):
        """Comprehensively delete participant and all related data"""
        try:
            participant_id = participant.id
            participant_email = participant.email
            
            # Delete related records in correct order
            tables_to_clean = [
                ("public_registrations", "participant_id", participant_id),
                ("accommodation_allocations", "participant_id", participant_id),
                ("participant_qr_codes", "participant_id", participant_id),
                ("event_allocations", "created_by", participant_email),
                ("notifications", "user_email", participant_email),
                ("user_fcm_tokens", "user_email", participant_email),
                ("participant_voucher_redemptions", "participant_id", participant_id),
                ("pending_voucher_redemptions", "participant_id", participant_id),
                ("transport_requests", "user_email", participant_email),
                ("flight_itineraries", "user_email", participant_email),
                ("travel_tickets", "user_email", participant_email),
                ("passport_records", "user_email", participant_email),
                ("perdiem_requests", "participant_id", participant_id),
            ]
            
            for table_name, column_name, value in tables_to_clean:
                try:
                    # Check if table exists first
                    table_exists = db.execute(
                        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"),
                        {"table_name": table_name}
                    ).scalar()
                    
                    if not table_exists:
                        continue
                        
                    count_result = db.execute(
                        text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :value"),
                        {"value": value}
                    )
                    count = count_result.scalar()
                    
                    if count > 0:
                        db.execute(
                            text(f"DELETE FROM {table_name} WHERE {column_name} = :value"),
                            {"value": value}
                        )
                        logger.info(f"Deleted {count} records from {table_name}")
                        
                except Exception as e:
                    logger.warning(f"Could not clean {table_name}: {e}")
                    # Rollback and start fresh transaction for next table
                    db.rollback()
                    db.begin()
            
            # Delete the participant record
            db.delete(participant)
            db.commit()
            
            logger.info(f"Successfully deleted participant {participant_id} and all related data")
            
        except Exception as e:
            logger.error(f"Error deleting participant data: {str(e)}")
            db.rollback()
            raise
