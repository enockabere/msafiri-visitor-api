import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.claim_conversation import ClaimConversation, ClaimConversationMessage
from app.services.claim_agent.agent import run_agent

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_or_create_conversation(
        self, conversation_id: Optional[int] = None
    ) -> ClaimConversation:
        """Get an existing conversation or create a new one."""
        if conversation_id:
            conversation = (
                self.db.query(ClaimConversation)
                .filter(
                    ClaimConversation.id == conversation_id,
                    ClaimConversation.user_id == self.user_id,
                )
                .first()
            )
            if conversation:
                return conversation

        # Create new conversation
        conversation = ClaimConversation(
            user_id=self.user_id,
            title="New Conversation",
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        logger.info(f"Created new conversation {conversation.id} for user {self.user_id}")
        return conversation

    def _update_title(self, conversation: ClaimConversation, user_message: str):
        """Set the conversation title from the first user message."""
        if conversation.title == "New Conversation":
            title = user_message[:100].strip()
            if len(user_message) > 100:
                title += "..."
            conversation.title = title
            self.db.commit()

    def _load_message_history(
        self, conversation_id: int
    ) -> List[Dict[str, Any]]:
        """Load previous messages for the conversation in LangChain-compatible format."""
        messages = (
            self.db.query(ClaimConversationMessage)
            .filter(ClaimConversationMessage.conversation_id == conversation_id)
            .order_by(ClaimConversationMessage.created_at)
            .all()
        )

        history = []
        for msg in messages:
            entry = {
                "role": msg.role,
                "content": msg.content or "",
            }
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_results:
                entry["tool_results"] = msg.tool_results
            history.append(entry)
        return history

    def _save_user_message(
        self,
        conversation_id: int,
        content: str,
        image_url: Optional[str] = None,
    ) -> ClaimConversationMessage:
        """Persist a user message."""
        msg = ClaimConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=content,
            image_url=image_url,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def _save_assistant_message(
        self,
        conversation_id: int,
        content: str,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None,
    ) -> ClaimConversationMessage:
        """Persist an assistant message with optional tool data."""
        msg = ClaimConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    async def chat(
        self,
        message: str,
        conversation_id: Optional[int] = None,
        image_url: Optional[str] = None,
    ) -> dict:
        """Process a user chat message through the AI agent.

        Returns:
            dict with conversation_id, message, tool_results, conversation_title
        """
        # Get or create conversation
        conversation = self.get_or_create_conversation(conversation_id)
        self._update_title(conversation, message)

        # Save user message
        self._save_user_message(conversation.id, message, image_url)

        # Load history (excluding the message we just saved — it will be passed separately)
        history = self._load_message_history(conversation.id)
        # Remove the last entry (the user message we just saved) since we pass it separately
        if history and history[-1]["role"] == "user":
            history = history[:-1]

        # Run the agent
        result = await run_agent(
            db=self.db,
            user_id=self.user_id,
            message_history=history,
            user_message=message,
            image_url=image_url,
        )

        # Save assistant response
        tool_results_data = result.get("tool_results", [])
        self._save_assistant_message(
            conversation_id=conversation.id,
            content=result["response"],
            tool_calls=[
                {"name": tr["tool_name"], "id": tr.get("tool_call_id", ""), "args": tr.get("args", {})}
                for tr in tool_results_data
            ]
            if tool_results_data
            else None,
            tool_results=tool_results_data if tool_results_data else None,
        )

        # Update timestamp
        conversation.updated_at = datetime.utcnow()
        self.db.commit()

        return {
            "conversation_id": conversation.id,
            "message": result["response"],
            "tool_results": [
                {"tool_name": tr["tool_name"], "result": tr.get("result", {})}
                for tr in tool_results_data
            ],
            "conversation_title": conversation.title,
        }

    def list_conversations(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """List the user's recent conversations."""
        conversations = (
            self.db.query(ClaimConversation)
            .filter(ClaimConversation.user_id == self.user_id)
            .order_by(ClaimConversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        results = []
        for conv in conversations:
            msg_count = (
                self.db.query(func.count(ClaimConversationMessage.id))
                .filter(ClaimConversationMessage.conversation_id == conv.id)
                .scalar()
            )
            results.append(
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "message_count": msg_count or 0,
                }
            )
        return results

    def get_conversation_detail(self, conversation_id: int) -> Optional[dict]:
        """Get a conversation with all its messages."""
        conversation = (
            self.db.query(ClaimConversation)
            .filter(
                ClaimConversation.id == conversation_id,
                ClaimConversation.user_id == self.user_id,
            )
            .first()
        )
        if not conversation:
            return None

        messages = (
            self.db.query(ClaimConversationMessage)
            .filter(ClaimConversationMessage.conversation_id == conversation_id)
            .order_by(ClaimConversationMessage.created_at)
            .all()
        )

        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                    "tool_results": msg.tool_results,
                    "image_url": msg.image_url,
                    "created_at": msg.created_at,
                }
                for msg in messages
            ],
        }

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conversation = (
            self.db.query(ClaimConversation)
            .filter(
                ClaimConversation.id == conversation_id,
                ClaimConversation.user_id == self.user_id,
            )
            .first()
        )
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()
        return True
