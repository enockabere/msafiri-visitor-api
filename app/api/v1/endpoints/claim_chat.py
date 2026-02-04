import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.claim_conversation import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    ConversationDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_conversation_service(db: Session, user_id: int):
    """Lazy import to avoid crashing the app if langchain is not installed."""
    try:
        from app.services.claim_agent.conversation_service import ConversationService
        return ConversationService(db, user_id)
    except ImportError as e:
        logger.error(f"LangChain dependencies not installed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI chat service is not available. LangChain dependencies are not installed.",
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to the AI expense claims agent."""
    logger.info(
        f"Chat request from user {current_user.id}: "
        f"conversation_id={request.conversation_id}, "
        f"message='{request.message[:50]}...'"
    )
    try:
        service = _get_conversation_service(db, current_user.id)
        result = await service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            image_url=request.image_url,
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}",
        )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's recent conversations."""
    service = _get_conversation_service(db, current_user.id)
    conversations = service.list_conversations(limit=limit, offset=offset)
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a conversation with all its messages."""
    service = _get_conversation_service(db, current_user.id)
    detail = service.get_conversation_detail(conversation_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return detail


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation."""
    service = _get_conversation_service(db, current_user.id)
    deleted = service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return {"message": "Conversation deleted successfully"}
