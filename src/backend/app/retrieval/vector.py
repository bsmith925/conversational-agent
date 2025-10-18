from typing import List, Dict, Any
from .base import RetrievalService
from app.database import DatabaseService
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorRetrieval(RetrievalService):
    """Vector similarity-based document retrieval."""

    def __init__(self, database: DatabaseService):
        self.database = database

    async def retrieve_documents(
        self,
        query: str,
        embedding: List[float],
        k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using vector similarity search."""
        logger.info(f"Retrieving documents for query: '{query[:100]}...'")

        # Convert embedding to PostgreSQL vector format
        embedding_str = f"[{','.join(map(str, embedding))}]"

        # vector similarity search '<=>'
        sql = """
            SELECT content, source_file, page_num, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM documents 
            ORDER BY embedding <=> %s::vector 
            LIMIT %s
        """

        # Get 2*k candidates initially for filtering
        params = (embedding_str, embedding_str, k * 2)
        results = await self.database.execute_query(sql, params)

        # Filter by similarity threshold and limit to k
        filtered_docs = [
            {
                "content": row["content"],
                "source": row["source_file"],
                "page": row["page_num"],
                "similarity": row["similarity"],
            }
            for row in results
            if row["similarity"] > similarity_threshold
        ][:k]

        logger.info(
            f"Retrieved {len(filtered_docs)} documents (threshold: {similarity_threshold})"
        )
        return filtered_docs
