from typing import Annotated
from functools import lru_cache
from fastapi import Depends
from sentence_transformers import SentenceTransformer
from app.services.rag.retrieval import Retriever
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_embedding_model() -> SentenceTransformer:
    """Singleton embedding model."""
    logger.info(f"Loading embedding model: {settings.embedding_model_name}")
    model = SentenceTransformer(settings.embedding_model_name, device='cpu')
    logger.info("Embedding model loaded")
    return model


def get_retriever() -> Retriever:
    """Dependency that provides a Retriever instance."""
    return Retriever()


# Type alias for dependency injection
RetrieverDep = Annotated[Retriever, Depends(get_retriever)]
EmbeddingModel = Annotated[SentenceTransformer, Depends(get_embedding_model)]