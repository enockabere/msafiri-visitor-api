# File: app/api/v1/endpoints/invitations.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.crud.invitation import invitation as crud_invitation
from app.schemas.invitation import InvitationCreate, Invitation as InvitationSchema
from app.models.invitation import Invitation
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.core.email_service import email_service
from datetime import datetime, timedelta
from app.core.config import settings
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=dict)
def create_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_in: InvitationCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Create new invitation for a tenant admin user."""
    logger.info(f"🎯 Invitation endpoint called by user: {current_user.email}")
    logger.info(f"📧 Invitation data: {invitation_in.dict()}")
    
    try:
        # Check permissions - only super admin or tenant admin can invite
        logger.info(f"👤 Current user role: {current_user.role}")
        if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
            logger.warning(f"❌ Permission denied for role: {current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
        # If not super admin, can only invite for own tenant
        logger.info(f"🏢 Checking tenant access: user_tenant={current_user.tenant_id}, invite_tenant={invitation_in.tenant_id}")
        if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != invitation_in.tenant_id:
            logger.warning(f"❌ Tenant access denied: {current_user.tenant_id} != {invitation_in.tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only invite users for your own tenant"
            )
    
        # Check if user already exists
        logger.info(f"🔍 Checking if user exists: {invitation_in.email}")
        existing_user = crud.user.get_by_email(db, email=invitation_in.email)
        if existing_user and existing_user.tenant_id == invitation_in.tenant_id:
            logger.warning(f"❌ User already exists: {invitation_in.email} for tenant {invitation_in.tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists for this tenant"
            )
    
        # Check if invitation already exists
        logger.info(f"🔍 Checking existing invitations for: {invitation_in.email}")
        existing_invitation = crud_invitation.get_by_email_and_tenant(
            db, email=invitation_in.email, tenant_id=invitation_in.tenant_id
        )
        if existing_invitation and existing_invitation.expires_at > datetime.utcnow():
            logger.warning(f"❌ Active invitation exists: {invitation_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active invitation already exists for this email"
            )
    
        # Create invitation
        logger.info(f"✨ Creating invitation token")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
        
        # Create invitation object directly with all required fields
        from app.models.invitation import Invitation
        invitation_obj = Invitation(
            email=invitation_in.email,
            full_name=invitation_in.full_name,
            role=invitation_in.role,
            tenant_id=invitation_in.tenant_id,
            token=token,
            expires_at=expires_at,
            invited_by=current_user.email,
            is_accepted="false"
        )
        
        logger.info(f"💾 Saving invitation to database")
        try:
            db.add(invitation_obj)
            db.flush()  # Flush to get any database errors before commit
            logger.info(f"💾 Invitation flushed, ID: {invitation_obj.id}")
            db.commit()
            logger.info(f"✅ Invitation committed successfully")
            db.refresh(invitation_obj)
            invitation = invitation_obj
        except Exception as db_error:
            logger.error(f"💥 Database error: {str(db_error)}")
            db.rollback()
            raise
        
        # Send invitation email
        logger.info(f"📧 Queuing invitation email")
        background_tasks.add_task(
            email_service.send_invitation_email,
            email=invitation_in.email,
            full_name=invitation_in.full_name,
            tenant_name=invitation_in.tenant_id,  # You might want to get actual tenant name
            token=token,
            invited_by=current_user.full_name or current_user.email,
            role=invitation_in.role
        )
        
        logger.info(f"✅ Invitation created successfully for {invitation_in.email}")
        return {"message": "Invitation sent successfully"}
        
    except Exception as e:
        logger.error(f"💥 Error creating invitation: {str(e)}")
        logger.exception("Full error traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invitation: {str(e)}"
        )

@router.get("/tenant/{tenant_id}", response_model=List[InvitationSchema])
def get_tenant_invitations(
    *,
    db: Session = Depends(get_db),
    tenant_id: str
) -> Any:
    """Get all pending invitations for a specific tenant."""
    invitations = crud_invitation.get_by_tenant(db, tenant_id=tenant_id)
    return invitations

@router.post("/{invitation_id}/resend", response_model=dict)
def resend_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Resend an invitation email."""
    invitation = crud_invitation.get(db, id=invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only resend for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != invitation.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only resend invitations for your own tenant"
        )
    
    # Update expiry date
    new_expires_at = datetime.utcnow() + timedelta(days=7)
    crud_invitation.update(db, db_obj=invitation, obj_in={"expires_at": new_expires_at})
    
    # Resend invitation email
    background_tasks.add_task(
        email_service.send_invitation_email,
        email=invitation.email,
        full_name=invitation.full_name,
        tenant_name=invitation.tenant_id,
        token=invitation.token,
        invited_by=current_user.full_name or current_user.email,
        role=invitation.role
    )
    
    return {"message": "Invitation resent successfully"}

@router.get("/check-pending/{email}", response_model=List[dict])
def check_pending_invitations(
    *,
    db: Session = Depends(get_db),
    email: str
) -> Any:
    """Check for pending invitations for an email address."""
    logger.info(f"🔍 Checking pending invitations for: {email}")
    
    try:
        # Find all pending invitations for this email
        invitations = db.query(Invitation).filter(
            Invitation.email == email,
            Invitation.is_accepted == "false",
            Invitation.expires_at > datetime.utcnow()
        ).all()
        
        result = []
        for invitation in invitations:
            result.append({
                "id": invitation.id,
                "email": invitation.email,
                "tenant_id": invitation.tenant_id,
                "role": invitation.role,
                "token": invitation.token,
                "expires_at": invitation.expires_at.isoformat()
            })
        
        logger.info(f"✅ Found {len(result)} pending invitations for {email}")
        return result
        
    except Exception as e:
        logger.error(f"💥 Error checking pending invitations: {str(e)}")
        return []


def debug_invitation(
    *,
    db: Session = Depends(get_db),
    token: str
) -> Any:
    """Debug endpoint to check invitation details"""
    logger.info(f"🔍 DEBUG: Checking invitation token: {token[:10]}...")
    
    invitation = crud_invitation.get_by_token(db, token=token)
    if not invitation:
        logger.info(f"🔍 DEBUG: No invitation found for token")
        return {"found": False, "token": token[:10] + "..."}
    
    logger.info(f"🔍 DEBUG: Found invitation - ID: {invitation.id}, Email: {invitation.email}, Role: {invitation.role}, Accepted: {invitation.is_accepted}")
    return {
        "found": True,
        "id": invitation.id,
        "email": invitation.email,
        "role": invitation.role,
        "tenant_id": invitation.tenant_id,
        "is_accepted": invitation.is_accepted,
        "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None
    }
def cancel_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Cancel an invitation."""
    invitation = crud_invitation.get(db, id=invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only cancel for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != invitation.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only cancel invitations for your own tenant"
        )
    
    # Delete the invitation
    db.delete(invitation)
    db.commit()
    
    return {"message": "Invitation cancelled successfully"}

@router.delete("/{invitation_id}/cancel", response_model=dict)
def cancel_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Cancel an invitation."""
    invitation = crud_invitation.get(db, id=invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only cancel for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != invitation.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only cancel invitations for your own tenant"
        )
    
    # Delete the invitation
    db.delete(invitation)
    db.commit()
    
    return {"message": "Invitation cancelled successfully"}

@router.post("/create-test-invitation", response_model=dict)
def create_test_invitation(
    *,
    db: Session = Depends(get_db)
) -> Any:
    """Create a test invitation for debugging"""
    print(f"\n🧪 CREATING TEST INVITATION")
    
    import secrets
    from datetime import datetime, timedelta
    from app.models.invitation import Invitation
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation_obj = Invitation(
        email="test@example.com",
        full_name="Test User",
        role="staff",
        tenant_id="msf-eastern-africa",
        token=token,
        expires_at=expires_at,
        invited_by="system",
        is_accepted="false"
    )
    
    db.add(invitation_obj)
    db.commit()
    db.refresh(invitation_obj)
    
    test_url = f"{settings.FRONTEND_URL}/accept-invitation?token={token}"
    print(f"🧪 Test invitation created: {test_url}")
    
    return {
        "message": "Test invitation created",
        "token": token,
        "url": test_url
    }

@router.post("/test-endpoint", response_model=dict)
def test_endpoint() -> Any:
    """Simple test endpoint to verify API connectivity"""
    print(f"\n🚨 TEST ENDPOINT HIT! 🚨")
    print(f"🚨 Timestamp: {datetime.utcnow()}")
    print(f"🚨 " + "="*30)
    return {"message": "Test endpoint working", "timestamp": datetime.utcnow().isoformat()}

@router.post("/accept/{token}", response_model=dict)
def accept_invitation(
    *,
    db: Session = Depends(get_db),
    token: str
) -> Any:
    """Accept an invitation using the token."""
    print(f"\n🚨 INVITATION ACCEPTANCE ENDPOINT HIT! 🚨")
    print(f"🚨 Token received: {token[:10]}...")
    print(f"🚨 Full token: {token}")
    print(f"🚨 Timestamp: {datetime.utcnow()}")
    print(f"🚨 " + "="*50)
    
    logger.info(f"🎯 Accept invitation called with token: {token[:10]}...")
    
    try:
        # Debug: Log the exact token being searched
        logger.info(f"🔍 Searching for exact token: '{token}'")
        logger.info(f"🔍 Token length: {len(token)}")
        
        # Find invitation by token
        invitation = crud_invitation.get_by_token(db, token=token)
        if not invitation:
            # Check if this is an admin invitation token
            from app.crud.admin_invitations import admin_invitation
            admin_inv = admin_invitation.get_by_token(db, token=token)
            if admin_inv:
                logger.info(f"🔄 Redirecting to admin invitation acceptance")
                # This is an admin invitation, redirect to the proper endpoint
                from app.api.v1.endpoints.super_admin import accept_super_admin_invitation
                from app.schemas.admin_invitations import AdminInvitationAccept
                return accept_super_admin_invitation(
                    db=db,
                    accept_data=AdminInvitationAccept(token=token)
                )
            
            # Debug: Check if token exists without expiry/acceptance filters
            any_invitation = db.query(Invitation).filter(Invitation.token == token).first()
            if any_invitation:
                logger.warning(f"❌ Token found but expired/accepted: expires_at={any_invitation.expires_at}, is_accepted={any_invitation.is_accepted}")
            else:
                logger.warning(f"❌ Token not found in database at all")
            
            logger.warning(f"❌ Invitation not found for token: {token[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation token"
            )
        
        # Check if invitation is expired
        if invitation.expires_at < datetime.utcnow():
            logger.warning(f"❌ Invitation expired: {invitation.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )
        
        # Check if already accepted
        if invitation.is_accepted == "true":
            logger.warning(f"❌ Invitation already accepted: {invitation.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted"
            )
        
        # Check if user already exists
        existing_user = crud.user.get_by_email(db, email=invitation.email)
        
        if existing_user:
            # Add user to new tenant
            logger.info(f"🔄 Adding role to existing user: {invitation.email}")
            from app.models.user_roles import UserRole as UserRoleModel
            from app.models.user_tenants import UserTenant
            
            # Use original role names
            role_value = invitation.role.lower()
            
            # Check if user already has this role
            existing_role = db.query(UserRoleModel).filter(
                UserRoleModel.user_id == existing_user.id,
                UserRoleModel.role == role_value.upper()
            ).first()
            
            if not existing_role:
                # Remove Guest role if user is getting a real role
                if role_value != "guest":
                    guest_roles = db.query(UserRoleModel).filter(
                        UserRoleModel.user_id == existing_user.id,
                        UserRoleModel.role == "GUEST"
                    ).all()
                    for guest_role in guest_roles:
                        db.delete(guest_role)
                
                # Add new role
                new_role = UserRoleModel(
                    user_id=existing_user.id,
                    role=role_value.upper()
                )
                db.add(new_role)
                logger.info(f"➕ Added role {role_value} to user {invitation.email}")
            else:
                logger.info(f"ℹ️ User {invitation.email} already has role {role_value}")
            
            # Add user to tenant if not already there
            existing_tenant_assignment = db.query(UserTenant).filter(
                UserTenant.user_id == existing_user.id,
                UserTenant.tenant_id == invitation.tenant_id
            ).first()
            
            if not existing_tenant_assignment:
                logger.info(f"⚠️ Skipping UserTenant creation due to database enum mismatch - user already has role in user_roles table")
            else:
                logger.info(f"ℹ️ User {invitation.email} already assigned to tenant {invitation.tenant_id}")
                
            existing_user.is_active = True
        else:
            # Create new user account
            from app.models.user import User, UserRole, UserStatus, AuthProvider
            import hashlib
            
            # Generate temporary password
            temp_password = "password@1234"
            hashed_password = hashlib.sha256(temp_password.encode()).hexdigest()
            
            user_obj = User(
                email=invitation.email,
                full_name=invitation.full_name,
                hashed_password=hashed_password,
                role=UserRole(invitation.role),
                status=UserStatus.ACTIVE,
                tenant_id=invitation.tenant_id,
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                must_change_password=True
            )
            
            logger.info(f"💾 Creating user account: {invitation.email}")
            db.add(user_obj)
            db.flush()  # Get the user ID
            
            # Create corresponding UserRole entry
            from app.models.user_roles import UserRole as UserRoleModel
            
            # Use original role name
            role_value = invitation.role.lower()
            
            user_role = UserRoleModel(
                user_id=user_obj.id,
                role=role_value.upper()
            )
            db.add(user_role)
            logger.info(f"➕ Added role {role_value} to new user {invitation.email}")
        
        # Mark invitation as accepted
        invitation.is_accepted = "true"
        invitation.accepted_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ Invitation accepted successfully for {invitation.email}")
        return {
            "message": "Invitation accepted successfully",
            "must_change_password": True
        }
        
    except Exception as e:
        logger.error(f"💥 Error accepting invitation: {str(e)}")
        logger.exception("Full error traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )