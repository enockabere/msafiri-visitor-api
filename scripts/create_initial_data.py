# File: scripts/create_initial_data.py (UPDATED for SSO compatibility)
"""
Script to create initial data for testing
Run this after setting up the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app import crud, schemas
from app.models.user import UserRole, AuthProvider  # Added AuthProvider import

def create_initial_data():
    db = SessionLocal()
    
    try:
        # Create initial tenant
        tenant_data = schemas.TenantCreate(
            name="MSF Kenya",
            slug="msf-kenya",
            contact_email="admin@msf-kenya.org",
            description="MSF Kenya Operation Center"
        )
        
        existing_tenant = crud.tenant.get_by_slug(db, slug=tenant_data.slug)
        if not existing_tenant:
            tenant = crud.tenant.create(db, obj_in=tenant_data)
            print(f"Created tenant: {tenant.name}")
        else:
            tenant = existing_tenant
            print(f"Tenant already exists: {tenant.name}")
        
        # Create super admin user
        super_admin_data = schemas.UserCreate(
            email="superadmin@msafiri.org",
            password="admin123",  # Change this in production!
            full_name="Super Administrator",
            role=UserRole.SUPER_ADMIN,
            tenant_id=None,  # Super admins don't belong to specific tenant
            auth_provider=AuthProvider.LOCAL  # Added this field
        )
        
        existing_super_admin = crud.user.get_by_email(db, email=super_admin_data.email)
        if not existing_super_admin:
            super_admin = crud.user.create(db, obj_in=super_admin_data)
            print(f"Created super admin: {super_admin.email}")
        else:
            print(f"Super admin already exists: {existing_super_admin.email}")
        
        # Create MT Admin for the tenant
        mt_admin_data = schemas.UserCreate(
            email="mtadmin@msf-kenya.org",
            password="admin123",  # Change this in production!
            full_name="MT Administrator",
            role=UserRole.MT_ADMIN,
            tenant_id=tenant.slug,
            auth_provider=AuthProvider.LOCAL  # Added this field
        )
        
        existing_mt_admin = crud.user.get_by_email(db, email=mt_admin_data.email, tenant_id=tenant.slug)
        if not existing_mt_admin:
            mt_admin = crud.user.create(db, obj_in=mt_admin_data)
            print(f"Created MT admin: {mt_admin.email}")
        else:
            print(f"MT admin already exists: {existing_mt_admin.email}")
        
        # Create a test visitor
        visitor_data = schemas.UserCreate(
            email="visitor@example.com",
            password="visitor123",
            full_name="Test Visitor",
            role=UserRole.VISITOR,
            tenant_id=tenant.slug,
            phone_number="+254700123456",
            auth_provider=AuthProvider.LOCAL  # Added this field
        )
        
        existing_visitor = crud.user.get_by_email(db, email=visitor_data.email, tenant_id=tenant.slug)
        if not existing_visitor:
            visitor = crud.user.create(db, obj_in=visitor_data)
            print(f"Created test visitor: {visitor.email}")
        else:
            print(f"Test visitor already exists: {existing_visitor.email}")
        
        # Create a few more test users for variety
        additional_users = [
            {
                "email": "hradmin@msf-kenya.org",
                "password": "admin123",
                "full_name": "HR Administrator",
                "role": UserRole.HR_ADMIN,
                "department": "Human Resources"
            },
            {
                "email": "staff@msf-kenya.org",
                "password": "staff123",
                "full_name": "Staff Member",
                "role": UserRole.STAFF,
                "department": "Operations"
            },
            {
                "email": "guest@external.com",
                "password": "guest123",
                "full_name": "External Guest",
                "role": UserRole.GUEST,
                "department": "External"
            }
        ]
        
        for user_info in additional_users:
            user_data = schemas.UserCreate(
                email=user_info["email"],
                password=user_info["password"],
                full_name=user_info["full_name"],
                role=user_info["role"],
                tenant_id=tenant.slug,
                auth_provider=AuthProvider.LOCAL,
                department=user_info.get("department"),
                phone_number="+254700123456"
            )
            
            existing_user = crud.user.get_by_email(db, email=user_data.email, tenant_id=tenant.slug)
            if not existing_user:
                new_user = crud.user.create(db, obj_in=user_data)
                print(f"Created {user_info['role'].value}: {new_user.email}")
            else:
                print(f"User already exists: {existing_user.email}")
        
        print("\nInitial data creation completed!")
        print("\n📋 Test Credentials for Swagger:")
        print("=" * 50)
        print("1. Super Admin: superadmin@msafiri.org / admin123")
        print("2. MT Admin: mtadmin@msf-kenya.org / admin123 (tenant: msf-kenya)")
        print("3. HR Admin: hradmin@msf-kenya.org / admin123 (tenant: msf-kenya)")
        print("4. Staff: staff@msf-kenya.org / staff123 (tenant: msf-kenya)")
        print("5. Visitor: visitor@example.com / visitor123 (tenant: msf-kenya)")
        print("6. Guest: guest@external.com / guest123 (tenant: msf-kenya)")
        print("\n🌐 Start server: uvicorn app.main:app --reload")
        print("📖 Swagger UI: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"Error creating initial data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_data()