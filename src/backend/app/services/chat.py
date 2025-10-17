from app.services.rag.service import RAGService
from app.services.cache import RedisChatMessageHistory
from app.models.chat import ChatMessage
from app.models.rag import RAGResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service that handles the common chat flow used by both REST and WebSocket."""

    def __init__(
        self, rag_service: RAGService, history_manager: RedisChatMessageHistory
    ):
        self.rag_service = rag_service
        self.history_manager = history_manager

    async def process_message(self, message: str, session_id: str) -> RAGResult:
        """Process a chat message through the full pipeline."""
        logger.info(
            f"Processing message: '{message[:100]}...' for session: {session_id}"
        )

        # 1. Get chat history
        messages = await self.history_manager.get_messages(
            session_id, limit=settings.chat_history_limit
        )
        formatted_history = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in messages]
        )

        logger.info(f"Chat history has {len(messages)} messages")

        # 2. Process through RAG
        result = await self.rag_service.process_query(
            question=message, chat_history=formatted_history
        )

        # 3. Save user message
        await self.history_manager.add_message(
            session_id, ChatMessage(role="user", content=message)
        )

        # 4. Save assistant response
        await self.history_manager.add_message(
            session_id,
            ChatMessage(
                role="assistant",
                content=result.answer,
                retrieved_context=[doc.model_dump() for doc in result.retrieved_docs],
            ),
        )

        logger.info("Message processing complete")

        # 5. Return result
        return result
