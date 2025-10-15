import chainlit as cl
import psycopg
import dspy
import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer
# lettudetect has to wait on torch >= 2.6.0
# from lettucedetect.detector import LTLMDetector
from config import settings
from typing import List

embedding_model = SentenceTransformer(settings.embedding_model_name, device='cpu')
#verifier = LTLMDetector(device="cpu")
lm = dspy.LM(model=f"ollama/{settings.llm_model}") #max_token
dspy.settings.configure(lm=lm)


async def retrieve_from_postgres(query: str, k: int = 5) -> List[str]:
    """
    An async function to retrieve documents from Postgres.
    Returns a list of document passages.
    """
    results = []
    # TODO: move pg to a dependency
    async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as aconn:
        async with aconn.cursor() as acur:
            query_embedding = embedding_model.encode(query, convert_to_tensor=False)
            await acur.execute(
                "SELECT content FROM documents ORDER BY embedding <=> %s LIMIT %s",
                (np.array(query_embedding), k),
            )
            retrieved_docs = [row[0] async for row in acur]
            results.extend(retrieved_docs)
    return results


class RAGSignature(dspy.Signature):
    """Answer questions based on context, with conversation history awareness."""
    # TODO: as a pydantic model for easy added validation when we get to responses to avoid breaking a UI
    # at a minimum add type hints
    context = dspy.InputField(desc="Relevant documents.")  
    question = dspy.InputField(desc="The user's question.")
    # TODO: at least call out a lot of the nuance to handling chat history (e.g., compacting long context)
    chat_history = dspy.InputField(desc="The history of the conversation")
    answer = dspy.OutputField(desc="A comphrensive and factual answer based on the context")


class RAG(dspy.Module):
    """The core DSPy program that performs RAG."""
    def __init__(self):
        super().__init__()
        self.generate_answer = dspy.ChainOfThought(RAGSignature)
        # TODO: parameterize so we can pass this in when we instantiate singleton of module
        self.k = 3
    # Thinking more on chat history, user context needs to be handled. So chat storage module needs to handle a key.
    # Define Redis objects and how they function (chat, message, etc)
    # then we don't need to pass in chat_history necessarily but can recall it by context variables
    async def aforward(self, question, chat_history):
        """Forward pass for the RAG module."""
        # 1. Retrieve context
        context = await retrieve_from_postgres(question, k=self.k)

        # 2. Generate an answer using the retrieved context
        prediction = await self.generate_answer.acall(
            context=context,
            question=question,
            chat_history=chat_history
        )

# Could add intent and slotting like LexV2 to swap in different system prompts (docstrings)
# RAGSignature.__doc__ = ""    