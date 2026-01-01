#!/usr/bin/env python3
"""
Script to create default transport provider record
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.transport_provider import TransportProvider
from datetime import datetime

def create_default_transport_provider():
    db: Session = SessionLocal()
    try:
        # Check if record already exists
        existing = db.query(TransportProvider).filter(
            TransportProvider.tenant_id == 1,
            TransportProvider.provider_name == "absolute_cabs"
        ).first()
        
        if existing:
            print("Transport provider 'absolute_cabs' already exists")
            return
        
        # Create new record
        provider = TransportProvider(
            tenant_id=1,
            provider_name="absolute_cabs",
            is_enabled=False,
            client_id="",
            client_secret="",
            hmac_secret="",
            api_base_url="",
            token_url="",
            created_by="system",
            created_at=datetime.utcnow()
        )
        
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        print(f"Created transport provider record with ID: {provider.id}")
        
    except Exception as e:
        print(f"Error creating transport provider: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_default_transport_provider()