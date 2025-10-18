from abc import ABC, abstractmethod
from typing import List


class EmbeddingService(ABC):
    """Base class for embedding services."""

    @abstractmethod
    async def encode(self, text: str) -> List[float]:
        """Encode text into embedding vector."""
        pass
