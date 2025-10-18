import asyncio
import dspy
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExtractKeywords(dspy.Signature):
    """From a question and chat history, extract key entities and concepts for a search query."""

    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    keywords = dspy.OutputField(
        desc="A comma-separated list of key entities, topics, and concepts."
    )


class GenerateHypotheticalAnswer(dspy.Signature):
    """Given a question and history, generate a hypothetical ideal answer to use for searching."""

    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    hypothetical_answer = dspy.OutputField(
        desc="A detailed, paragraph-length hypothetical answer as if found in a perfect document."
    )


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
            self.generate_hyde.acall(question=question, chat_history=chat_history),
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
