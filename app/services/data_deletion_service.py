from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.event_participant import EventParticipant
from app.models.event import Event
import logging

logger = logging.getLogger(__name__)

class DataDeletionService:
    """Service for handling automatic data deletion based on data protection policies"""
    
    @staticmethod
    def delete_sensitive_data_for_participant(db: Session, participant_id: int) -> bool:
        """Delete sensitive personal data for a specific participant while keeping audit trail"""
        try:
            participant = db.query(EventParticipant).filter(EventParticipant.id == participant_id).first()
            if not participant:
                return False
            
            # Skip if already deleted
            if participant.data_deleted_at:
                logger.info(f"Data already deleted for participant {participant_id}")
                return True
            
            # Store original email hash for audit trail
            import hashlib
            if participant.email and not participant.original_email_hash:
                participant.original_email_hash = hashlib.sha256(participant.email.encode()).hexdigest()[:64]
            
            # Fields to anonymize for data protection
            sensitive_fields = {
                'personal_email': '[DELETED]',
                'msf_email': '[DELETED]',
                'hrco_email': '[DELETED]',
                'career_manager_email': '[DELETED]',
                'line_manager_email': '[DELETED]',
                'phone_number': '[DELETED]',
                'dietary_requirements': '[DELETED]',
                'accommodation_needs': '[DELETED]',
                'motivation_letter': '[DELETED]',
                'nationality': '[DELETED]',
                'country': '[DELETED]',
                'country_of_work': '[DELETED]',
                'current_position': '[DELETED]',
                'project_of_work': '[DELETED]',
                'gender_identity': '[DELETED]',
                'sex': '[DELETED]',
                'pronouns': '[DELETED]',
                'oc': '[DELETED]',
                'contract_status': '[DELETED]',
                'contract_type': '[DELETED]',
                'passport_document': None,
                'ticket_document': None,
                'eta': '[DELETED]',
                'vetting_comments': '[DELETED]'
            }
            
            # Update participant with anonymized data
            for field, value in sensitive_fields.items():
                if hasattr(participant, field):
                    setattr(participant, field, value)
            
            # Mark as data deleted
            participant.full_name = f"[DELETED PARTICIPANT {participant_id}]"
            participant.email = f"deleted.{participant_id}@data-protection.msf"
            participant.data_deleted_at = datetime.utcnow()
            participant.data_deletion_reason = "automatic_data_protection"
            
            db.commit()
            logger.info(f"Sensitive data deleted for participant {participant_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting sensitive data for participant {participant_id}: {e}")
            return False
    
    @staticmethod
    def delete_cancelled_participant_data(db: Session, participant_id: int) -> bool:
        """Immediately delete sensitive data for cancelled participants"""
        return DataDeletionService.delete_sensitive_data_for_participant(db, participant_id)
    
    @staticmethod
    def get_participants_for_monthly_deletion(db: Session) -> list:
        """Get participants whose data should be deleted (1 month after event completion)"""
        try:
            # Get events that ended more than 30 days ago
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            result = db.execute(text("""
                SELECT ep.id, ep.full_name, ep.email, ep.status, e.title, e.end_date
                FROM event_participants ep
                JOIN events e ON ep.event_id = e.id
                WHERE e.end_date < :cutoff_date
                AND ep.status NOT IN ('not_selected', 'canceled', 'declined')
                AND ep.email NOT LIKE 'deleted.%@data-protection.msf'
                AND ep.full_name NOT LIKE '[DELETED PARTICIPANT %]'
                AND ep.data_deleted_at IS NULL
            """), {"cutoff_date": cutoff_date})
            
            return [dict(row._mapping) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting participants for monthly deletion: {e}")
            return []
    
    @staticmethod
    def get_participants_for_immediate_deletion(db: Session) -> list:
        """Get participants whose data should be deleted immediately (2 days after status change)"""
        try:
            # Get participants with not_selected, canceled, or declined status older than 2 days
            cutoff_date = datetime.utcnow() - timedelta(days=2)
            
            result = db.execute(text("""
                SELECT ep.id, ep.full_name, ep.email, ep.status, e.title, ep.updated_at
                FROM event_participants ep
                JOIN events e ON ep.event_id = e.id
                WHERE ep.status IN ('not_selected', 'canceled', 'declined')
                AND ep.updated_at < :cutoff_date
                AND ep.email NOT LIKE 'deleted.%@data-protection.msf'
                AND ep.full_name NOT LIKE '[DELETED PARTICIPANT %]'
                AND ep.data_deleted_at IS NULL
            """), {"cutoff_date": cutoff_date})
            
            return [dict(row._mapping) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting participants for immediate deletion: {e}")
            return []
    
    @staticmethod
    def process_automatic_deletions(db: Session) -> dict:
        """Process all automatic data deletions"""
        results = {
            "immediate_deletions": 0,
            "monthly_deletions": 0,
            "errors": []
        }
        
        try:
            # Process immediate deletions (2 days after rejection/cancellation)
            immediate_participants = DataDeletionService.get_participants_for_immediate_deletion(db)
            for participant in immediate_participants:
                if DataDeletionService.delete_sensitive_data_for_participant(db, participant['id']):
                    results["immediate_deletions"] += 1
                    logger.info(f"Immediate deletion processed for participant {participant['id']}")
                else:
                    results["errors"].append(f"Failed immediate deletion for participant {participant['id']}")
            
            # Process monthly deletions (30 days after event completion)
            monthly_participants = DataDeletionService.get_participants_for_monthly_deletion(db)
            for participant in monthly_participants:
                if DataDeletionService.delete_sensitive_data_for_participant(db, participant['id']):
                    results["monthly_deletions"] += 1
                    logger.info(f"Monthly deletion processed for participant {participant['id']}")
                else:
                    results["errors"].append(f"Failed monthly deletion for participant {participant['id']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in automatic deletion process: {e}")
            results["errors"].append(f"Process error: {str(e)}")
            return results
