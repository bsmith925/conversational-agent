from typing import List
from pydantic import BaseModel


class RetrievedDocument(BaseModel):
    """A retrieved document from the vector database."""

    content: str
    source: str
    page: int
    similarity: float


class RAGResult(BaseModel):
    """Result from the RAG pipeline."""

    answer: str
    retrieved_docs: List[RetrievedDocument]
    search_query: str
