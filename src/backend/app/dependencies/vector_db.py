from typing import Annotated
from functools import lru_cache
from fastapi import Depends
from sentence_transformers import SentenceTransformer
from app.services.database import VectorDatabase
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


def get_vector_database(
    embedding_model: Annotated[SentenceTransformer, Depends(get_embedding_model)]
) -> VectorDatabase:
    """Dependency that provides a VectorDatabase instance."""
    return VectorDatabase(embedding_model)


# Type alias for dependency injection
VectorDB = Annotated[VectorDatabase, Depends(get_vector_database)]