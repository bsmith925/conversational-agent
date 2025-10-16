from typing import Annotated
from fastapi import Depends
import dspy
from app.services.rag import RAGService
from app.dependencies.vector_db import VectorDB
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize DSPy LM once at module level
# TODO: remove the global
_dspy_initialized = False


def initialize_dspy():
    """Initialize DSPy configuration once."""
    global _dspy_initialized
    
    if not _dspy_initialized:
        lm = dspy.LM(
            model="openrouter/google/gemini-2.5-pro",
            max_tokens=settings.llm_max_tokens
        )
        dspy.settings.configure(lm=lm)
        _dspy_initialized = True
        logger.info("DSPy LM initialized")


def get_rag_service(vector_db: VectorDB) -> RAGService:
    """Dependency that provides a RAG service."""
    initialize_dspy()
    return RAGService(vector_db, k=settings.rag_k)


# Type alias for dependency injection
RAGDep = Annotated[RAGService, Depends(get_rag_service)]