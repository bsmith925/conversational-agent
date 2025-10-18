from functools import lru_cache
from fastapi import Depends
from app.embeddings import EmbeddingService, SentenceTransformersEmbedding
from app.retrieval import RetrievalService, VectorRetrieval
from app.dependencies.database import get_database_service


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Singleton embedding service."""
    return SentenceTransformersEmbedding()


def get_retrieval_service(database=Depends(get_database_service)) -> RetrievalService:
    """Request-scoped retrieval service."""
    return VectorRetrieval(database)
