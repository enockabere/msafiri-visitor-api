from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
import logging


logger = logging.getLogger(__name__)


class CRUDTenant(CRUDBase[Tenant, TenantCreate, TenantUpdate]):
    def get_by_slug(self, db: Session, *, slug: str) -> Optional[Tenant]:
        return db.query(Tenant).filter(Tenant.slug == slug).first()
    
    def get_by_public_id(self, db: Session, *, public_id: str) -> Optional[Tenant]:
        try:
            return db.query(Tenant).filter(Tenant.public_id == public_id).first()
        except Exception:
            # If public_id column doesn't exist, return None
            return None
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[Tenant]:
        return db.query(Tenant).filter(Tenant.name == name).first()
    
    def get_by_domain(self, db: Session, *, domain: str) -> Optional[Tenant]:
        return db.query(Tenant).filter(Tenant.domain == domain).first()
    
    def create_with_notifications(self, db: Session, *, obj_in: TenantCreate, created_by: str) -> Tenant:
        """Create tenant and trigger notifications"""
        tenant = self.create(db, obj_in=obj_in)
        
        # Send notifications
        from app.core.enhanced_notifications import notification_service
        try:
            notification_service.notify_tenant_created(
                db,
                tenant=tenant,
                created_by=created_by
            )
        except Exception as e:
            logger.error(f"Failed to send tenant creation notifications for {tenant.name}: {e}")
        
        return tenant
    
    def update_status_with_notifications(
        self,
        db: Session,
        *,
        tenant: Tenant,
        is_active: bool,
        changed_by: str
    ) -> Tenant:
        """Update tenant status and send notifications"""
        old_active = tenant.is_active
        
        # Update status
        updated_tenant = self.update(db, db_obj=tenant, obj_in={"is_active": is_active})
        
        # Determine action for notifications
        if not old_active and is_active:
            action = "activated"
        elif old_active and not is_active:
            action = "deactivated"
        else:
            action = None
        
        # Send notifications if status actually changed
        if action:
            from app.core.enhanced_notifications import notification_service
            try:
                notification_service.notify_tenant_status_changed(
                    db,
                    tenant=updated_tenant,
                    action=action,
                    changed_by=changed_by
                )
            except Exception as e:
                logger.error(f"Failed to send tenant status change notifications for {tenant.name}: {e}")
        
        return updated_tenant

tenant = CRUDTenant(Tenant)
