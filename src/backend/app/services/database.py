from typing import List, Dict, Any
import psycopg
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# I'm not sure on how I want to name & split yet. 
# I'll need to do a pass over with SOLID principles.
# First thought, class Retrieval as a service. That uses VectorDB dep.
class VectorDatabase:
    """Service for vector database operations."""
    
    def __init__(self, embedding_model: SentenceTransformer):
        self.embedding_model = embedding_model
    
    async def retrieve_documents(
        self, 
        query: str, 
        k: int = 5,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Retrieve documents from Postgres using vector similarity."""
        if similarity_threshold is None:
            similarity_threshold = settings.retrieval_similarity_threshold
            
        logger.info(f"Retrieving documents for query: '{query[:100]}...'")
        
        try:
            async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as aconn:
                async with aconn.cursor() as acur:
                    query_embedding = self.embedding_model.encode(
                        query, 
                        convert_to_tensor=False
                    )
                    embedding_list = query_embedding.tolist()
                    embedding_str = f"[{','.join(map(str, embedding_list))}]"
                    
                    # Get 2*k candidates initially for filtering
                    await acur.execute(
                        """SELECT content, source_file, page_num, 
                           1 - (embedding <=> %s::vector) as similarity
                           FROM documents 
                           ORDER BY embedding <=> %s::vector LIMIT %s""",
                        (embedding_str, embedding_str, k * 2),
                    )
                    
                    retrieved_docs = []
                    async for row in acur:
                        retrieved_docs.append({
                            "content": row[0],
                            "source": row[1],
                            "page": row[2],
                            "similarity": row[3]
                        })
                    
                    # Filter by similarity threshold
                    filtered_docs = [
                        doc for doc in retrieved_docs 
                        if doc.get("similarity", 0) > similarity_threshold
                    ][:k]
                    
                    logger.info(
                        f"Retrieved {len(filtered_docs)} documents "
                        f"(threshold: {similarity_threshold})"
                    )
                    
                    if filtered_docs:
                        similarities = [doc['similarity'] for doc in filtered_docs]
                        logger.info(f"Similarity scores: {[f'{s:.3f}' for s in similarities]}")
                    
                    return filtered_docs
                    
        except Exception as e:
            logger.error(f"Postgres retrieval failed: {e}", exc_info=True)
            return []