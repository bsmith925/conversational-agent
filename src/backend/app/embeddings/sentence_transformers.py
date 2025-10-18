from typing import List
from sentence_transformers import SentenceTransformer
from .base import EmbeddingService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# TODO: this is overly verbose, but I'm not sur eon the interface I want to do.
# Probably a map for the different approaches and drop this being a fullblown service.
class SentenceTransformersEmbedding(EmbeddingService):
    """Sentence Transformers implementation of embedding service."""

    def __init__(self):
        self.model = SentenceTransformer(settings.embedding_model_name)
        logger.info(f"Loaded embedding model: {settings.embedding_model_name}")

    async def encode(self, text: str) -> List[float]:
        """Encode text using Sentence Transformers."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
