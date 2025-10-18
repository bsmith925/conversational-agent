from typing import List, Dict, Any
from app.database import DatabaseService
from app.embeddings import EmbeddingService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# TODO: parameterize 2*k section
class HyDESearch:
    """HyDE (Hypothetical Document Embeddings) search strategy."""

    def __init__(self, database: DatabaseService, embedding: EmbeddingService):
        self.database = database
        self.embedding = embedding

    async def search(
        self,
        query: str,
        k: int = 5,
        similarity_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """Search using HyDE (Hypothetical Document Embeddings) strategy."""
        if similarity_threshold is None:
            similarity_threshold = settings.retrieval_similarity_threshold

        logger.info(f"HyDE search for query: '{query[:100]}...'")

        try:
            # Get embedding for the query
            query_embedding = await self.embedding.encode(query)
            embedding_str = f"[{','.join(map(str, query_embedding))}]"

            # SQL query for vector similarity search
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
                f"HyDE retrieved {len(filtered_docs)} documents (threshold: {similarity_threshold})"
            )

            return filtered_docs

        except Exception as e:
            logger.error(f"HyDE search failed: {e}", exc_info=True)
            return []
