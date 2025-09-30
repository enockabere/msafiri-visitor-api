#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def create_admin_invitation_tables():
    """Create admin invitation and user-tenant tables"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Create admin_invitations table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_invitations (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    invitation_token VARCHAR(255) UNIQUE NOT NULL,
                    invited_by VARCHAR(255) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    accepted_at TIMESTAMP WITH TIME ZONE,
                    user_existed BOOLEAN DEFAULT FALSE,
                    user_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # Create indexes for admin_invitations
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_admin_invitations_email ON admin_invitations(email);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_admin_invitations_token ON admin_invitations(invitation_token);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_admin_invitations_status ON admin_invitations(status);
            """))
            
            # Create user_tenants table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user_tenants (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id VARCHAR NOT NULL REFERENCES tenants(slug) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL DEFAULT 'staff',
                    is_active BOOLEAN DEFAULT TRUE,
                    is_primary BOOLEAN DEFAULT FALSE,
                    assigned_by VARCHAR(255) NOT NULL,
                    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    deactivated_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, tenant_id)
                );
            """))
            
            # Create indexes for user_tenants
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_tenants_user_id ON user_tenants(user_id);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant_id ON user_tenants(tenant_id);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_tenants_role ON user_tenants(role);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_tenants_is_primary ON user_tenants(is_primary);
            """))
            
            # Commit the transaction
            connection.commit()
            
            print("Admin invitation and user-tenant tables created successfully!")
            
    except SQLAlchemyError as e:
        print(f"Error creating tables: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Creating admin invitation and user-tenant tables...")
    success = create_admin_invitation_tables()
    
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")
        sys.exit(1)