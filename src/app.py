import chainlit as cl
import psycopg
import dspy
import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer
# lettudetect has to wait on torch >= 2.6.0
# from lettucedetect.detector import LTLMDetector
from config import settings
from typing import List, Dict, Any
from chat_history import RedisChatMessageHistory, ChatMessage

embedding_model = SentenceTransformer(settings.embedding_model_name, device='cpu')
#verifier = LTLMDetector(device="cpu")
lm = dspy.LM(model=f"ollama/{settings.llm_model}", max_tokens=300) #max_token
dspy.settings.configure(lm=lm)


async def retrieve_from_postgres(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    An async function to retrieve documents from Postgres.
    Returns a list of dictionaries, each containing the passage and its source.
    """
    results = []
    # TODO: move pg to a dependency
    async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as aconn:
        async with aconn.cursor() as acur:
            query_embedding = embedding_model.encode(query, convert_to_tensor=False)
            embedding_list = query_embedding.tolist()
            embedding_str = f"[{','.join(map(str, embedding_list))}]"
            await acur.execute(
                """SELECT content, source_file, page_num FROM documents 
                ORDER BY embedding <=> %s LIMIT %s""",
                (embedding_str, k),
            )
            retrieved_docs = [
                {"content": row[0], "source": row[1], "page": row[2]} async for row in acur
            ]
            results.extend(retrieved_docs)
    return results


class RAGSignature(dspy.Signature):
    """Answer questions based on context, with conversation history awareness."""
    # TODO: as a pydantic model for easy added validation when we get to responses to avoid breaking a UI
    context: List[str] = dspy.InputField(desc="Relevant documents.")  
    question: str = dspy.InputField(desc="The user's question.")
    # TODO: at least call out a lot of the nuance to handling chat history (e.g., compacting long context)
    chat_history: str = dspy.InputField(desc="The history of the conversation")
    answer: str = dspy.OutputField(desc="A comphrensive and factual answer based on the context")

RAGSignature.__doc__ = """
    You are a helpful and knowledgeable assistant specializing in the history of the House of Tudor.
    Answer the user's questions based *only* on the context provided.
    Be friendly and conversational. If the context does not contain the answer, say so politely.
"""

class RAG(dspy.Module):
    """The core DSPy program that performs RAG."""
    def __init__(self, k: int = 3) -> None:
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
        retrieved_docs = await retrieve_from_postgres(question, k=self.k)
        context_passages = [doc['content'] for doc in retrieved_docs]


        # 2. Generate an answer using the retrieved context
        prediction = await self.generate_answer.acall(
            context=context_passages,
            question=question,
            chat_history=chat_history
        )

        return prediction


# Could add intent and slotting like LexV2 to swap in different system prompts (docstrings)
rag = RAG(k=5)
# Chainlit
@cl.on_chat_start
async def start_chat():
    """Initializes the user session."""
    redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
    history_manager = RedisChatMessageHistory(session_id=cl.user_session.get("id"), redis_client=redis_client)
    cl.user_session.set("history_manager", history_manager)
    cl.user_session.set("rag_chain", rag)
    
    await cl.Message(
        content="Hello! I am a historical assistant specializing in the House of Tudor. How many I help you?"
    ).send()
    
@cl.on_message
async def main(message: cl.Message):
    """Handles incoming user messages and runs the RAG pipeline."""
    rag_chain = cl.user_session.get("rag_chain")
    history_manager: RedisChatMessageHistory = cl.user_session.get("history_manager")

    # TODO: again comment on compacting long history.
    # simple string join to start
    formatted_history = await history_manager.get_formatted_string()
    msg = cl.Message(content="")
    await msg.send()

    try:
        prediction = await rag_chain.acall(
            question=message.content,
            chat_history=formatted_history
        )
        final_answer = prediction.answer
        

        await msg.stream_token(final_answer)

        await history_manager.add_message(ChatMessage(role="user", content=message.content))
        await history_manager.add_message(ChatMessage(role="assistant", content=final_answer))

    except Exception as e:
        await msg.stream_token(f"An error occurred: {e}")

    await msg.update()
        



