#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_minimal():
    """Test minimal imports"""
    
    try:
        # Test model imports only
        from app.models.event_participant import EventParticipant
        from app.models.event_attachment import EventAttachment
        print("Models import successfully")
        
        # Test direct endpoint imports
        import app.api.v1.endpoints.event_participants
        import app.api.v1.endpoints.event_attachments
        print("Endpoint modules import successfully")
        
        print("Basic imports working - server should start!")
        
    except Exception as e:
        print(f"Import error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minimal()