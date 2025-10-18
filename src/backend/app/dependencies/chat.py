from fastapi import Depends
from app.services.chat import ChatService, ChatCache
from app.retrieval import RAGService
from app.database import RedisDatabase
from app.dependencies.database import get_redis_database
from app.dependencies.retrieval import get_embedding_service
from app.dependencies.database import get_database_service
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_chat_cache(redis_db: RedisDatabase = Depends(get_redis_database)) -> ChatCache:
    """Dependency that provides a ChatCache."""
    return ChatCache(redis_db, ttl=settings.redis_ttl)


def get_rag_service(
    embedding=Depends(get_embedding_service),
    database=Depends(get_database_service),
) -> RAGService:
    """Dependency that provides a RAG service."""
    try:
        return RAGService(embedding, database, k=settings.rag_k)
    except Exception as e:
        logger.error(f"Failed to create RAG service: {e}", exc_info=True)
        raise


def get_chat_service(
    cache=Depends(get_chat_cache),
    rag_service=Depends(get_rag_service),
) -> ChatService:
    """Dependency that provides a ChatService."""
    try:
        return ChatService(rag_service, cache)
    except Exception as e:
        logger.error(f"Failed to create ChatService: {e}", exc_info=True)
        raise
