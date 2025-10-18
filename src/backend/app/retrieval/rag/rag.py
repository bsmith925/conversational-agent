from typing import List
import dspy
from app.embeddings import EmbeddingService
from app.database import DatabaseService
from .search.hyde import HyDESearch
from app.core.config import settings
from app.core.logging import get_logger
from app.models.rag import RAGResult, RetrievedDocument
from .query.engine import QueryUnderstandingEngine

logger = get_logger(__name__)


class FinalAnswerSignature(dspy.Signature):
    """Answer questions based on context from the knowledge base and the conversation history."""

    context: List[str] = dspy.InputField(
        desc="Relevant documents from the knowledge base."
    )
    question: str = dspy.InputField(desc="The user's original, unmodified question.")
    chat_history: str = dspy.InputField(desc="Recent conversation history for context.")
    answer: str = dspy.OutputField(
        desc="A comprehensive and accurate answer based ONLY on the provided context."
    )


# Update the docstring for stricter guidance
FinalAnswerSignature.__doc__ = """You are a helpful and knowledgeable AI assistant.
CRITICAL RULES:
1. Answer ONLY based on the `context` provided. If the context does not contain the answer, state that clearly.
2. Use the `chat_history` to understand pronouns and follow-up questions.
3. Reference the source of your information, e.g., 'According to [Source: file.pdf, Page: 3], ...'
4. Be precise and accurate. If the context is insufficient, explicitly state that."""

# TODO: Service naming convention removal after refactor fully complete
class RAGService:
    """RAG service with query understanding and answer generation."""

    def __init__(
        self,
        embedding: EmbeddingService,
        database: DatabaseService,
        k: int = None,
    ):
        self.embedding = embedding
        self.database = database
        self.k = k or settings.rag_k
        self.query_engine = QueryUnderstandingEngine()
        self.search_strategy = HyDESearch(database, embedding)
        self.generate_answer = dspy.ChainOfThought(FinalAnswerSignature)

    async def process_query(self, question: str, chat_history: str) -> RAGResult:
        """Process a query through the RAG pipeline."""

        # Understand query
        search_query = await self.query_engine.aforward(question, chat_history)

        # Search using HyDE strategy
        retrieved_docs = await self.search_strategy.search(search_query, k=self.k)

        # Handle no context
        # TODO: handle this better. not sure yet.
        if not retrieved_docs:
            logger.warning("No relevant documents found for the synthesized query.")
            return RAGResult(
                answer="I couldn't find any information about that in my knowledge base. "
                "Could you try asking in a different way?",
                retrieved_docs=[],
                search_query=search_query,
            )

        # Step 4: Generate answer
        context_passages = [
            f"[Source: {doc['source']}, Page: {doc['page']}]\n{doc['content']}"
            for doc in retrieved_docs
        ]

        prediction = await self.generate_answer.acall(
            context=context_passages,
            question=question,  # Use original question
            chat_history=chat_history,
        )

        logger.info(f"Answer generated (length: {len(prediction.answer)} chars)")

        retrieved_doc_models = [RetrievedDocument(**doc) for doc in retrieved_docs]

        return RAGResult(
            answer=prediction.answer,
            retrieved_docs=retrieved_doc_models,
            search_query=search_query,
        )
