from abc import ABC, abstractmethod
from typing import List, Dict, Any


class RetrievalService(ABC):
    """Base class for document retrieval services."""

    @abstractmethod
    async def retrieve_documents(
        self,
        query: str,
        embedding: List[float],
        k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Retrieve documents based on query and embedding."""
        pass
