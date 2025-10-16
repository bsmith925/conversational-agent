import asyncio
from typing import List
import dspy
from app.services.database import VectorDatabase
from app.core.config import settings
from app.core.logging import get_logger
from app.models.rag import RAGResult, RetrievedDocument

logger = get_logger(__name__)


# DSPY SIGNATURES
class ExtractKeywords(dspy.Signature):
    """From a question and chat history, extract key entities and concepts for a search query."""
    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    keywords = dspy.OutputField(desc="A comma-separated list of key entities, topics, and concepts.")


class GenerateHypotheticalAnswer(dspy.Signature):
    """Given a question and history, generate a hypothetical ideal answer to use for searching."""
    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    hypothetical_answer = dspy.OutputField(
        desc="A detailed, paragraph-length hypothetical answer as if found in a perfect document."
    )


class FinalAnswerSignature(dspy.Signature):
    """Answer questions based on context from the knowledge base and the conversation history."""
    context: List[str] = dspy.InputField(desc="Relevant documents from the knowledge base.")
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


class QueryUnderstandingEngine(dspy.Module):
    """A DSPy module dedicated to understanding the user's query in context."""
    
    def __init__(self):
        super().__init__()
        self.extract_keywords = dspy.Predict(ExtractKeywords)
        self.generate_hyde = dspy.Predict(GenerateHypotheticalAnswer)

    async def aforward(self, question: str, chat_history: str) -> str:
        """Takes raw user input and chat history, returns an optimized search query."""
        if not chat_history.strip():
            logger.info("First turn, using original question for search.")
            return question

        logger.info("Query Understanding Engine: Activated for multi-turn context.")
        
        # Run keyword extraction and HyDE generation in parallel
        keywords_pred, hyde_pred = await asyncio.gather(
            self.extract_keywords.acall(question=question, chat_history=chat_history),
            self.generate_hyde.acall(question=question, chat_history=chat_history)
        )
        
        keywords = keywords_pred.keywords
        hypothetical_answer = hyde_pred.hypothetical_answer
        
        # Combine into search query
        final_search_query = (
            f"{question} | Relevant concepts: {keywords} | "
            f"Potential answer context: {hypothetical_answer}"
        )
        
        logger.info(f"Original question: '{question}'")
        logger.info(f"Synthesized search query: '{final_search_query[:250]}...'")
        
        return final_search_query


class RAGService:
    """RAG service with query understanding and answer generation."""
    
    def __init__(self, vector_db: VectorDatabase, k: int = None):
        self.vector_db = vector_db
        self.k = k or settings.rag_k
        self.query_engine = QueryUnderstandingEngine()
        self.generate_answer = dspy.ChainOfThought(FinalAnswerSignature)
    
    async def process_query(
        self, 
        question: str, 
        chat_history: str
    ) -> RAGResult:
        """Process a query through the RAG pipeline."""
        
        # Understand query
        search_query = await self.query_engine.aforward(question, chat_history)
        
        # Retrieve documents
        retrieved_docs = await self.vector_db.retrieve_documents(
            search_query, 
            k=self.k
        )
        
        # Handle no context
        # TODO: handle this better. not sure yet.
        if not retrieved_docs:
            logger.warning("No relevant documents found for the synthesized query.")
            return RAGResult(
                answer="I couldn't find any information about that in my knowledge base. "
                       "Could you try asking in a different way?",
                retrieved_docs=[],
                search_query=search_query
            )
        
        # Step 4: Generate answer
        context_passages = [
            f"[Source: {doc['source']}, Page: {doc['page']}]\n{doc['content']}" 
            for doc in retrieved_docs
        ]
        
        prediction = await self.generate_answer.acall(
            context=context_passages,
            question=question,  # Use original question
            chat_history=chat_history
        )
        
        logger.info(f"Answer generated (length: {len(prediction.answer)} chars)")

        retrieved_doc_models = [
            RetrievedDocument(**doc) for doc in retrieved_docs
        ]
        
        return RAGResult(
            answer=prediction.answer,
            retrieved_docs=retrieved_doc_models,
            search_query=search_query
        )