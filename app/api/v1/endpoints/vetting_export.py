# File: app/api/v1/endpoints/vetting_export.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.event_participant import EventParticipant
from app.models.vetting_committee import VettingCommittee, ParticipantSelection

router = APIRouter()

@router.get("/{committee_id}/export")
def export_participant_data(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export participant data (privacy-compliant)"""
    
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if current_user.role not in [UserRole.VETTING_COMMITTEE, UserRole.VETTING_APPROVER, UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    # Get participants with selections
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == committee.event_id
    ).all()
    
    selections = db.query(ParticipantSelection).filter(
        ParticipantSelection.committee_id == committee_id
    ).all()
    
    selection_map = {s.participant_id: s for s in selections}
    
    # Create CSV data (excluding sensitive fields)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers (privacy-compliant - excludes gender, DoB, nationality, passport details)
    writer.writerow([
        'Full Name', 'Email', 'Country', 'Position', 'Project',
        'Status', 'Selected', 'Selection Notes', 'Selected By'
    ])
    
    # Data rows
    for participant in participants:
        selection = selection_map.get(participant.id)
        writer.writerow([
            participant.full_name,
            participant.email,
            participant.country or '',
            participant.position or '',
            participant.project or '',
            participant.status,
            'Yes' if selection and selection.selected else 'No' if selection else 'Pending',
            selection.selection_notes if selection else '',
            selection.selected_by if selection else ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="participants_committee_{committee_id}.csv"'}
    )