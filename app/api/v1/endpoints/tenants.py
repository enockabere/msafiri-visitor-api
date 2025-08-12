# File: app/api/v1/endpoints/tenants.py (ENHANCED)
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.core.enhanced_notifications import notification_service
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[schemas.TenantWithStats])
def read_tenants(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve tenants with user statistics."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenants = crud.tenant.get_multi(db, skip=skip, limit=limit)
    
    # Add user statistics for each tenant
    enhanced_tenants = []
    for tenant in tenants:
        # Get user statistics
        total_users = len(crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000))
        active_users = len([u for u in crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000) if u.is_active])
        pending_users = len([u for u in crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000) if u.status.value == "pending_approval"])
        
        # Get last user activity (simplified - you might want to track this separately)
        users = crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=5)
        last_activity = max([u.last_login for u in users if u.last_login], default=None)
        
        tenant_data = {
            **tenant.__dict__,
            "total_users": total_users,
            "active_users": active_users,
            "pending_users": pending_users,
            "last_user_activity": last_activity
        }
        enhanced_tenants.append(schemas.TenantWithStats(**tenant_data))
    
    return enhanced_tenants

@router.post("/", response_model=schemas.Tenant)
def create_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_in: schemas.TenantCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Create new tenant with enhanced notifications."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if tenant already exists
    existing_tenant = crud.tenant.get_by_slug(db, slug=tenant_in.slug)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this slug already exists"
        )
    
    # Prepare tenant data with tracking
    tenant_data = tenant_in.dict()
    tenant_data["created_by"] = current_user.email
    
    # Handle additional admin emails
    if tenant_in.additional_admin_emails:
        tenant_data["secondary_admin_emails"] = json.dumps([
            email.strip() for email in tenant_in.additional_admin_emails.split(',')
        ])
    
    # Create tenant
    tenant = crud.tenant.create(db, obj_in=schemas.TenantCreate(**tenant_data))
    
    # Send notifications in background
    background_tasks.add_task(
        send_tenant_creation_notifications,
        db, tenant, current_user.email
    )
    
    return tenant

@router.put("/{tenant_id}", response_model=schemas.Tenant)
def update_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    tenant_update: schemas.TenantEditRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Update tenant with change tracking and notifications."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Store original values for change tracking
    original_values = {
        "name": tenant.name,
        "description": tenant.description,
        "contact_email": tenant.contact_email,
        "admin_email": tenant.admin_email,
        "is_active": tenant.is_active
    }
    
    # Prepare update data
    update_data = tenant_update.changes.dict(exclude_unset=True)
    update_data["last_modified_by"] = current_user.email
    
    # Handle additional admin emails
    if hasattr(tenant_update.changes, 'additional_admin_emails') and tenant_update.changes.additional_admin_emails:
        update_data["secondary_admin_emails"] = json.dumps([
            email.strip() for email in tenant_update.changes.additional_admin_emails.split(',')
        ])
    
    # Update tenant
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in=update_data)
    
    # Track changes and send notifications
    if tenant_update.notify_admins:
        background_tasks.add_task(
            send_tenant_update_notifications,
            db, updated_tenant, original_values, 
            tenant_update.reason, current_user.email
        )
    
    return updated_tenant

@router.post("/activate/{tenant_id}", response_model=schemas.Tenant)
def activate_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Activate a tenant with notifications."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is already active"
        )
    
    # Activate tenant
    from sqlalchemy import func
    update_data = {
        "is_active": True,
        "activated_at": func.now(),
        "last_modified_by": current_user.email
    }
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in=update_data)
    
    # Send notifications
    background_tasks.add_task(
        send_tenant_status_change_notifications,
        db, updated_tenant, "activated", current_user.email
    )
    
    return updated_tenant

@router.post("/deactivate/{tenant_id}", response_model=schemas.Tenant)
def deactivate_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Deactivate a tenant with notifications."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is already inactive"
        )
    
    # Deactivate tenant
    from sqlalchemy import func
    update_data = {
        "is_active": False,
        "deactivated_at": func.now(),
        "last_modified_by": current_user.email
    }
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in=update_data)
    
    # Send notifications
    background_tasks.add_task(
        send_tenant_status_change_notifications,
        db, updated_tenant, "deactivated", current_user.email
    )
    
    return updated_tenant

@router.get("/{tenant_id}", response_model=schemas.TenantWithStats)
def read_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get tenant by ID with statistics."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Add statistics
    total_users = len(crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000))
    active_users = len([u for u in crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000) if u.is_active])
    pending_users = len([u for u in crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000) if u.status.value == "pending_approval"])
    
    users = crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=5)
    last_activity = max([u.last_login for u in users if u.last_login], default=None)
    
    tenant_data = {
        **tenant.__dict__,
        "total_users": total_users,
        "active_users": active_users,
        "pending_users": pending_users,
        "last_user_activity": last_activity
    }
    
    return schemas.TenantWithStats(**tenant_data)

# Background task functions
def send_tenant_creation_notifications(db: Session, tenant, created_by: str):
    """Send notifications about tenant creation"""
    try:
        # Get all admin emails to notify
        admin_emails = []
        
        # Primary admin email
        if tenant.admin_email:
            admin_emails.append(tenant.admin_email)
        
        # Contact email (if different)
        if tenant.contact_email and tenant.contact_email not in admin_emails:
            admin_emails.append(tenant.contact_email)
        
        # Additional admin emails
        if tenant.secondary_admin_emails:
            additional_emails = json.loads(tenant.secondary_admin_emails)
            admin_emails.extend([email for email in additional_emails if email not in admin_emails])
        
        # Send email notifications
        if admin_emails:
            from app.core.email import email_service
            
            subject = f"New Organization Created: {tenant.name}"
            
            for email in admin_emails:
                try:
                    html_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #007bff;">New Organization Created</h1>
                        
                        <p>A new organization has been created in the Msafiri system:</p>
                        
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0;">Organization Details:</h3>
                            <ul>
                                <li><strong>Name:</strong> {tenant.name}</li>
                                <li><strong>Slug:</strong> {tenant.slug}</li>
                                <li><strong>Contact Email:</strong> {tenant.contact_email}</li>
                                <li><strong>Created By:</strong> {created_by}</li>
                                <li><strong>Description:</strong> {tenant.description or 'Not provided'}</li>
                            </ul>
                        </div>
                        
                        <p>You are receiving this email because you are listed as an administrator for this organization.</p>
                        
                        <p>If you have any questions, please contact the system administrator.</p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        
                        <p style="color: #666; font-size: 14px;">
                            This is an automated notification from the Msafiri System.
                        </p>
                    </body>
                    </html>
                    """
                    
                    email_service.send_email([email], subject, html_content)
                    logger.info(f"Tenant creation email sent to {email}")
                    
                except Exception as e:
                    logger.error(f"Failed to send tenant creation email to {email}: {e}")
        
        # Use existing notification service for super admins
        notification_service.notify_tenant_created(db, tenant=tenant, created_by=created_by)
        
    except Exception as e:
        logger.error(f"Failed to send tenant creation notifications: {e}")

def send_tenant_update_notifications(db: Session, tenant, original_values: dict, reason: str, updated_by: str):
    """Send notifications about tenant updates"""
    try:
        # Determine what changed
        changes = []
        current_values = {
            "name": tenant.name,
            "description": tenant.description,
            "contact_email": tenant.contact_email,
            "admin_email": tenant.admin_email,
            "is_active": tenant.is_active
        }
        
        for field, original_value in original_values.items():
            current_value = current_values.get(field)
            if original_value != current_value:
                changes.append(f"{field}: '{original_value}' → '{current_value}'")
        
        if not changes:
            return  # No actual changes
        
        # Get admin emails
        admin_emails = []
        if tenant.admin_email:
            admin_emails.append(tenant.admin_email)
        if tenant.contact_email and tenant.contact_email not in admin_emails:
            admin_emails.append(tenant.contact_email)
        if tenant.secondary_admin_emails:
            additional_emails = json.loads(tenant.secondary_admin_emails)
            admin_emails.extend([email for email in additional_emails if email not in admin_emails])
        
        # Send notifications
        if admin_emails:
            from app.core.email import email_service
            
            subject = f"Organization Updated: {tenant.name}"
            
            changes_html = "<ul>" + "".join([f"<li>{change}</li>" for change in changes]) + "</ul>"
            
            for email in admin_emails:
                try:
                    html_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #fd7e14;">Organization Updated</h1>
                        
                        <p>The organization <strong>{tenant.name}</strong> has been updated:</p>
                        
                        <div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0;">Changes Made:</h3>
                            {changes_html}
                            
                            <p><strong>Reason:</strong> {reason}</p>
                            <p><strong>Updated By:</strong> {updated_by}</p>
                        </div>
                        
                        <p>If you have any questions about these changes, please contact the system administrator.</p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        
                        <p style="color: #666; font-size: 14px;">
                            This is an automated notification from the Msafiri System.
                        </p>
                    </body>
                    </html>
                    """
                    
                    email_service.send_email([email], subject, html_content)
                    logger.info(f"Tenant update email sent to {email}")
                    
                except Exception as e:
                    logger.error(f"Failed to send tenant update email to {email}: {e}")
        
    except Exception as e:
        logger.error(f"Failed to send tenant update notifications: {e}")

def send_tenant_status_change_notifications(db: Session, tenant, action: str, changed_by: str):
    """Send notifications about tenant status changes"""
    try:
        # Use existing notification service
        notification_service.notify_tenant_status_changed(
            db, tenant=tenant, action=action, changed_by=changed_by
        )
        
        # Also send direct emails to tenant admins
        admin_emails = []
        if tenant.admin_email:
            admin_emails.append(tenant.admin_email)
        if tenant.contact_email and tenant.contact_email not in admin_emails:
            admin_emails.append(tenant.contact_email)
        if tenant.secondary_admin_emails:
            additional_emails = json.loads(tenant.secondary_admin_emails)
            admin_emails.extend([email for email in additional_emails if email not in admin_emails])
        
        if admin_emails:
            from app.core.email import email_service
            
            color = "#28a745" if action == "activated" else "#dc3545"
            subject = f"Organization {action.title()}: {tenant.name}"
            
            for email in admin_emails:
                try:
                    html_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: {color};">Organization {action.title()}</h1>
                        
                        <p>The organization <strong>{tenant.name}</strong> has been <strong>{action}</strong> by {changed_by}.</p>
                        
                        <div style="background: {'#d4edda' if action == 'activated' else '#f8d7da'}; padding: 20px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 0;">
                                {'Your organization is now active and users can access the system.' if action == 'activated' 
                                 else 'Your organization has been temporarily deactivated. Users will not be able to access the system.'}
                            </p>
                        </div>
                        
                        <p>If you have questions about this change, please contact the system administrator.</p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        
                        <p style="color: #666; font-size: 14px;">
                            This is an automated notification from the Msafiri System.
                        </p>
                    </body>
                    </html>
                    """
                    
                    email_service.send_email([email], subject, html_content)
                    logger.info(f"Tenant {action} email sent to {email}")
                    
                except Exception as e:
                    logger.error(f"Failed to send tenant {action} email to {email}: {e}")
        
    except Exception as e:
        logger.error(f"Failed to send tenant status change notifications: {e}")