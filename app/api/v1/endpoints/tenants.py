# File: app/api/v1/endpoints/tenants.py (ENHANCED)
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.core.enhanced_notifications import notification_service
from app.core.tenant_admin_assignment import assign_user_to_tenant_on_admin_change
from app.utils.timezone_utils import auto_set_timezone
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
    # Allow access for various admin roles and tenant admins
    allowed_roles = [UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]
    
    # Also check if user is a tenant admin (has tenant_id)
    is_tenant_admin = hasattr(current_user, 'tenant_id') and current_user.tenant_id
    
    if current_user.role not in allowed_roles and not is_tenant_admin:
        print(f"DEBUG: Tenants access denied - User role: {current_user.role}, Tenant ID: {getattr(current_user, 'tenant_id', None)}")
        print(f"DEBUG: Allowed roles: {[role.value for role in allowed_roles]}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If user is tenant admin, only return their tenant
    if is_tenant_admin and current_user.role not in allowed_roles:
        tenant = crud.tenant.get_by_slug(db, slug=current_user.tenant_id)
        tenants = [tenant] if tenant else []
    else:
        tenants = crud.tenant.get_multi(db, skip=skip, limit=limit)
    
    # Add user statistics for each tenant
    enhanced_tenants = []
    for tenant in tenants:
        # Get user statistics from user_tenants table
        tenant_users = crud.user_tenant.get_tenant_users(db, tenant_id=tenant.slug)
        total_users = len(tenant_users)
        active_users = len([ut for ut in tenant_users if ut.is_active])
        
        # Get pending users (legacy support)
        legacy_users = crud.user.get_by_tenant(db, tenant_id=tenant.slug, limit=1000)
        pending_users = len([u for u in legacy_users if u.status.value == "pending_approval"])
        
        # Get last user activity from tenant users
        last_activity = None
        if tenant_users:
            user_ids = [ut.user_id for ut in tenant_users[:5]]
            users = [crud.user.get(db, id=uid) for uid in user_ids]
            users = [u for u in users if u and u.last_login]
            if users:
                last_activity = max([u.last_login for u in users])
        
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
    
    # Check if tenant already exists by slug
    existing_tenant = crud.tenant.get_by_slug(db, slug=tenant_in.slug)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this slug already exists"
        )
    
    # Check if tenant already exists by name
    existing_tenant_name = crud.tenant.get_by_name(db, name=tenant_in.name)
    if existing_tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this name already exists"
        )
    
    # Prepare tenant data with tracking
    tenant_data = tenant_in.dict()
    tenant_data["created_by"] = current_user.email
    
    # Auto-set timezone based on country
    tenant_data = auto_set_timezone(tenant_data)
    
    # Handle empty domain - convert to NULL to avoid unique constraint violation
    if "domain" in tenant_data and (tenant_data["domain"] == "" or tenant_data["domain"] is None):
        tenant_data["domain"] = None
    
    # Note: additional_admin_emails field has been removed
    
    # Create tenant
    tenant = crud.tenant.create(db, obj_in=schemas.TenantCreate(**tenant_data))
    
    # Auto-assign user to tenant if admin_email is provided
    if tenant.admin_email:
        assign_user_to_tenant_on_admin_change(db, tenant)
    
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
    
    # Auto-set timezone based on country if country is being updated
    if "country" in update_data:
        update_data = auto_set_timezone(update_data)
    
    # Handle empty domain - convert to NULL to avoid unique constraint violation
    if "domain" in update_data and (update_data["domain"] == "" or update_data["domain"] is None):
        update_data["domain"] = None
    
    # Force updated_at to be set
    from sqlalchemy import func
    update_data["updated_at"] = func.now()
    
    # Update tenant
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in=update_data)
    
    # Auto-assign user to tenant if admin_email changed
    if "admin_email" in update_data and update_data["admin_email"] != original_values["admin_email"]:
        assign_user_to_tenant_on_admin_change(db, updated_tenant, original_values["admin_email"])
    
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

@router.get("/public/{public_id}", response_model=schemas.TenantWithStats)
def read_tenant_by_public_id(
    *,
    db: Session = Depends(get_db),
    public_id: str,
) -> Any:
    """Get tenant by public_id (no auth required for dashboard)."""
    tenant = crud.tenant.get_by_public_id(db, public_id=public_id)
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
def read_tenant_by_slug(
    *,
    db: Session = Depends(get_db),
    tenant_slug: str,
) -> Any:
    """Get tenant by slug with statistics (no auth required for dashboard)."""
    tenant = crud.tenant.get_by_slug(db, slug=tenant_slug)
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

@router.get("/{tenant_slug}", response_model=schemas.TenantWithStats)
def read_tenant_by_slug_simple(
    *,
    db: Session = Depends(get_db),
    tenant_slug: str,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get tenant by slug with authentication and statistics."""
    tenant = crud.tenant.get_by_slug(db, slug=tenant_slug)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if user has access to this tenant
    if (current_user.role != UserRole.SUPER_ADMIN and 
        current_user.tenant_id != tenant_slug):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have permission to view this tenant"
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

@router.get("/by-id/{tenant_id}", response_model=schemas.TenantWithStats)
def read_tenant_by_id(
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

@router.post("/update-timezones")
def update_tenant_timezones(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Update timezones for all tenants based on their country."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from app.utils.timezone_utils import get_timezone_for_country
    
    # Get all tenants
    tenants = crud.tenant.get_multi(db, limit=1000)
    updated_count = 0
    
    for tenant in tenants:
        if tenant.country and not tenant.timezone:
            timezone = get_timezone_for_country(tenant.country)
            if timezone:
                update_data = {"timezone": timezone}
                crud.tenant.update(db, db_obj=tenant, obj_in=update_data)
                updated_count += 1
    
    return {
        "message": f"Updated {updated_count} tenants with automatic timezones",
        "updated_count": updated_count
    }

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
            from app.core.email_service import email_service
            
            subject = f"New MSF Tenant Created: {tenant.name}"

            for email in admin_emails:
                try:
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    </head>
                    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5;">
                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                                        <!-- Header with MSF Red -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                                    🏢 New MSF Tenant Created
                                                </h1>
                                            </td>
                                        </tr>

                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="font-size: 16px; color: #374151; margin: 0 0 25px 0;">
                                                    Great news! A new MSF tenant has been successfully created in the <strong>Msafiri system</strong>.
                                                </p>

                                                <!-- Tenant Details Card -->
                                                <div style="background: linear-gradient(to bottom, #fef2f2 0%, #ffffff 100%); border-left: 4px solid #dc2626; padding: 25px; border-radius: 8px; margin: 25px 0;">
                                                    <h2 style="color: #dc2626; font-size: 20px; margin: 0 0 20px 0; font-weight: 600;">
                                                        📋 Tenant Details
                                                    </h2>
                                                    <table width="100%" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
                                                        <tr>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2; width: 40%;">
                                                                <span style="color: #6b7280; font-weight: 500;">Tenant Name:</span>
                                                            </td>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <strong style="color: #111827; font-size: 15px;">{tenant.name}</strong>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <span style="color: #6b7280; font-weight: 500;">Tenant Slug:</span>
                                                            </td>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <code style="background-color: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-family: 'Courier New', monospace; color: #dc2626; font-size: 14px;">{tenant.slug}</code>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <span style="color: #6b7280; font-weight: 500;">Contact Email:</span>
                                                            </td>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <a href="mailto:{tenant.contact_email}" style="color: #dc2626; text-decoration: none; font-weight: 500;">{tenant.contact_email}</a>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <span style="color: #6b7280; font-weight: 500;">Created By:</span>
                                                            </td>
                                                            <td style="padding: 10px 0; border-bottom: 1px solid #fee2e2;">
                                                                <span style="color: #111827;">{created_by}</span>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 10px 0; vertical-align: top;">
                                                                <span style="color: #6b7280; font-weight: 500;">Description:</span>
                                                            </td>
                                                            <td style="padding: 10px 0;">
                                                                <span style="color: #4b5563; line-height: 1.6;">{tenant.description or '<em style="color: #9ca3af;">No description provided</em>'}</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </div>

                                                <!-- Info Box -->
                                                <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin: 25px 0;">
                                                    <p style="margin: 0; color: #1e40af; font-size: 14px;">
                                                        <strong>ℹ️ Administrator Notice:</strong><br>
                                                        You are receiving this email because you are listed as an administrator for this MSF tenant. You can now access the tenant dashboard and manage users, events, and resources.
                                                    </p>
                                                </div>

                                                <p style="font-size: 15px; color: #6b7280; margin: 25px 0 0 0;">
                                                    If you have any questions or need assistance, please contact the system administrator.
                                                </p>
                                            </td>
                                        </tr>

                                        <!-- Footer -->
                                        <tr>
                                            <td style="background-color: #f9fafb; padding: 25px 30px; border-top: 1px solid #e5e7eb;">
                                                <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center; line-height: 1.5;">
                                                    This is an automated notification from the <strong style="color: #6b7280;">Msafiri System</strong><br>
                                                    MSF Traveller Management • Médecins Sans Frontières
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
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
            from app.core.email_service import email_service
            
            subject = f"MSF Tenant Updated: {tenant.name}"

            changes_html = "".join([f"""
                                                        <tr>
                                                            <td style="padding: 8px 0; border-bottom: 1px solid #fee2e2;">
                                                                <span style="color: #4b5563;">• {change}</span>
                                                            </td>
                                                        </tr>""" for change in changes])

            for email in admin_emails:
                try:
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    </head>
                    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5;">
                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                                        <!-- Header with MSF Red -->
                                        <tr>
                                            <td style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 40px 30px; text-align: center;">
                                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                                    ✏️ MSF Tenant Updated
                                                </h1>
                                            </td>
                                        </tr>

                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="font-size: 16px; color: #374151; margin: 0 0 25px 0;">
                                                    The MSF tenant <strong style="color: #dc2626;">{tenant.name}</strong> has been updated with the following changes:
                                                </p>

                                                <!-- Changes Card -->
                                                <div style="background: linear-gradient(to bottom, #fffbeb 0%, #ffffff 100%); border-left: 4px solid #f59e0b; padding: 25px; border-radius: 8px; margin: 25px 0;">
                                                    <h2 style="color: #d97706; font-size: 20px; margin: 0 0 20px 0; font-weight: 600;">
                                                        📝 Changes Made
                                                    </h2>
                                                    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                                                        {changes_html}
                                                    </table>

                                                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #fef3c7;">
                                                        <p style="margin: 5px 0; color: #6b7280;">
                                                            <strong style="color: #111827;">Reason:</strong> {reason}
                                                        </p>
                                                        <p style="margin: 5px 0; color: #6b7280;">
                                                            <strong style="color: #111827;">Updated By:</strong> {updated_by}
                                                        </p>
                                                    </div>
                                                </div>

                                                <p style="font-size: 15px; color: #6b7280; margin: 25px 0 0 0;">
                                                    If you have any questions about these changes, please contact the system administrator.
                                                </p>
                                            </td>
                                        </tr>

                                        <!-- Footer -->
                                        <tr>
                                            <td style="background-color: #f9fafb; padding: 25px 30px; border-top: 1px solid #e5e7eb;">
                                                <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center; line-height: 1.5;">
                                                    This is an automated notification from the <strong style="color: #6b7280;">Msafiri System</strong><br>
                                                    MSF Traveller Management • Médecins Sans Frontières
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
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
            from app.core.email_service import email_service
            
            color = "#10b981" if action == "activated" else "#dc2626"
            gradient = "linear-gradient(135deg, #10b981 0%, #059669 100%)" if action == "activated" else "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)"
            bg_color = "#ecfdf5" if action == "activated" else "#fef2f2"
            border_color = "#10b981" if action == "activated" else "#dc2626"
            icon = "✅" if action == "activated" else "⛔"
            subject = f"MSF Tenant {action.title()}: {tenant.name}"

            for email in admin_emails:
                try:
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    </head>
                    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5;">
                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
                            <tr>
                                <td align="center">
                                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                                        <!-- Header -->
                                        <tr>
                                            <td style="background: {gradient}; padding: 40px 30px; text-align: center;">
                                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                                    {icon} MSF Tenant {action.title()}
                                                </h1>
                                            </td>
                                        </tr>

                                        <!-- Content -->
                                        <tr>
                                            <td style="padding: 40px 30px;">
                                                <p style="font-size: 16px; color: #374151; margin: 0 0 25px 0;">
                                                    The MSF tenant <strong style="color: #dc2626;">{tenant.name}</strong> has been <strong>{action}</strong> by <strong>{changed_by}</strong>.
                                                </p>

                                                <!-- Status Card -->
                                                <div style="background: {bg_color}; border-left: 4px solid {border_color}; padding: 25px; border-radius: 8px; margin: 25px 0;">
                                                    <h2 style="color: {color}; font-size: 18px; margin: 0 0 15px 0; font-weight: 600;">
                                                        {'🎉 Tenant is Now Active' if action == 'activated' else '⚠️ Tenant Deactivated'}
                                                    </h2>
                                                    <p style="margin: 0; color: #374151; line-height: 1.6;">
                                                        {'Your MSF tenant is now active! All administrators and users can access the system, manage resources, and utilize all features of the Msafiri platform.' if action == 'activated'
                                                         else 'Your MSF tenant has been temporarily deactivated. Users will not be able to access the system until it is reactivated by a system administrator.'}
                                                    </p>
                                                </div>

                                                <p style="font-size: 15px; color: #6b7280; margin: 25px 0 0 0;">
                                                    If you have questions about this change, please contact the system administrator.
                                                </p>
                                            </td>
                                        </tr>

                                        <!-- Footer -->
                                        <tr>
                                            <td style="background-color: #f9fafb; padding: 25px 30px; border-top: 1px solid #e5e7eb;">
                                                <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center; line-height: 1.5;">
                                                    This is an automated notification from the <strong style="color: #6b7280;">Msafiri System</strong><br>
                                                    MSF Traveller Management • Médecins Sans Frontières
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </body>
                    </html>
                    """
                    
                    email_service.send_email([email], subject, html_content)
                    logger.info(f"Tenant {action} email sent to {email}")
                    
                except Exception as e:
                    logger.error(f"Failed to send tenant {action} email to {email}: {e}")
        
    except Exception as e:
        logger.error(f"Failed to send tenant status change notifications: {e}")