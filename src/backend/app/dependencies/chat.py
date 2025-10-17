from typing import Annotated
from functools import lru_cache
from fastapi import Depends
from app.services.cache import RedisChatMessageHistory
from app.services.chat import ChatService
from app.dependencies.cache import RedisClient
from app.dependencies.rag import RAGDep
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_chat_history_manager(redis_client: RedisClient) -> RedisChatMessageHistory:
    """Dependency that provides a singleton chat history manager."""
    return RedisChatMessageHistory(
        redis_client=redis_client,
        ttl=settings.redis_ttl
    )


@lru_cache(maxsize=1)
def get_chat_service(
    rag_service: RAGDep,
    redis_client: RedisClient
) -> ChatService:
    """Dependency that provides a singleton ChatService."""
    try:
        history_manager = get_chat_history_manager(redis_client)
        return ChatService(rag_service, history_manager)
    except Exception as e:
        logger.error(f"Failed to create ChatService: {e}", exc_info=True)
        raise


# Type aliases for dependency injection
ChatHistoryManager = Annotated[RedisChatMessageHistory, Depends(get_chat_history_manager)]
RAGChatService = Annotated[ChatService, Depends(get_chat_service)]
