#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly"""
    
    try:
        # Test model imports
        from app.models.event_participant import EventParticipant
        from app.models.event_attachment import EventAttachment
        print("Models import successfully")
        
        # Test schema imports
        from app.schemas.event_participant import EventParticipantCreate
        print("Schemas import successfully")
        
        # Test service imports
        from app.services.notification_service import send_event_notifications
        print("Services import successfully")
        
        # Test API imports
        from app.api.v1.endpoints.event_participants import router as participants_router
        from app.api.v1.endpoints.event_attachments import router as attachments_router
        print("API endpoints import successfully")
        
        print("\nAll imports successful! Server should start without errors.")
        
    except Exception as e:
        print(f"Import error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()