from typing import Annotated
from fastapi import Depends
import dspy
from app.services.rag.service import RAGService
from app.dependencies.vector_db import RetrieverDep, EmbeddingModel
from app.dependencies.database import DatabaseConnection
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize DSPy LM at module level
lm = dspy.LM(
    model="openrouter/google/gemini-2.5-pro",
    max_tokens=settings.llm_max_tokens
)
dspy.settings.configure(lm=lm)


def get_rag_service(
    retriever: RetrieverDep,
    embedding_model: EmbeddingModel,
    db_connection: DatabaseConnection
) -> RAGService:
    """Dependency that provides a RAG service."""
    return RAGService(retriever, embedding_model, db_connection, k=settings.rag_k)


# Type alias for dependency injection
RAGDep = Annotated[RAGService, Depends(get_rag_service)]