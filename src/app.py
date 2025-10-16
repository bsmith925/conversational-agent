import chainlit as cl
import psycopg
import dspy
import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer
from config import settings
from typing import List, Dict, Any, Optional
from chat_history import RedisChatMessageHistory, ChatMessage
import logging
import asyncio

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MODEL & DSPY CONFIGURATION 
embedding_model = SentenceTransformer(settings.embedding_model_name, device='cpu')
lm = dspy.LM(model="openrouter/google/gemini-2.5-pro", max_tokens=settings.llm_max_tokens)
dspy.settings.configure(lm=lm)


# Retrieval
async def retrieve_from_postgres(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve documents from Postgres using vector similarity.
    """
    logger.info(f"Retrieving documents for query: '{query[:100]}...'")
    results = []
    try:
        async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as aconn:
            async with aconn.cursor() as acur:
                query_embedding = embedding_model.encode(query, convert_to_tensor=False)
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
                    if doc.get("similarity", 0) > settings.retrieval_similarity_threshold
                ][:k]
                
                logger.info(f"Retrieved {len(filtered_docs)} documents (threshold: {settings.retrieval_similarity_threshold})")
                if filtered_docs:
                    similarities = [doc['similarity'] for doc in filtered_docs]
                    logger.info(f"Similarity scores: {[f'{s:.3f}' for s in similarities]}")
                
                results.extend(filtered_docs)
    except Exception as e:
        logger.error(f"Postgres retrieval failed: {e}", exc_info=True)
        # TODO: handle upstream what happens when no documents found. Just raise a 'sorry' couldn't find. Or have LLM re-write the query.
        return []
    return results


# DSPY SIGNATURES & MODULES 

# Query Understanding 
# TODO: migrate to module.__doc__="" over in-class, unless DSPy no longer recommends
class ExtractKeywords(dspy.Signature):
    """From a question and chat history, extract key entities and concepts for a search query."""
    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    keywords = dspy.OutputField(desc="A comma-separated list of key entities, topics, and concepts.")

class GenerateHypotheticalAnswer(dspy.Signature):
    """Given a question and history, generate a hypothetical ideal answer to use for searching. This is the HyDE technique."""
    chat_history = dspy.InputField(desc="The recent conversation history.")
    question = dspy.InputField(desc="The user's latest question.")
    hypothetical_answer = dspy.OutputField(desc="A detailed, paragraph-length hypothetical answer as if found in a perfect document.")

class QueryUnderstandingEngine(dspy.Module):
    """A DSPy module dedicated to understanding the user's query in context."""
    def __init__(self):
        super().__init__()
        self.extract_keywords = dspy.Predict(ExtractKeywords)
        self.generate_hyde = dspy.Predict(GenerateHypotheticalAnswer)

    async def aforward(self, question: str, chat_history: str) -> str:
        """Takes raw user input and chat history, and returns a single, optimized search query."""
        if not chat_history.strip():
            logger.info("First turn, using original question for search.")
            return question

        logger.info("Query Understanding Engine: Activated for multi-turn context.")
        
        # Run keyword extraction and HyDE generation
        # TODO: evaluate/extract/ and evaluate/hyde/
        # Create train-test split for dspy optimizer
        # Save optimized program (pickled) for each program.
        keywords_pred, hyde_pred = await asyncio.gather(
            self.extract_keywords.acall(question=question, chat_history=chat_history),
            self.generate_hyde.acall(question=question, chat_history=chat_history)
        )
        
        keywords = keywords_pred.keywords
        hypothetical_answer = hyde_pred.hypothetical_answer
        
        # Combine everything into one powerful search query for the retrieval system
        # TODO: evaluate combined too?
        final_search_query = f"{question} | Relevant concepts: {keywords} | Potential answer context: {hypothetical_answer}"
        
        logger.info(f"Original question: '{question}'")
        logger.info(f"Synthesized search query: '{final_search_query[:250]}...'")
        
        return final_search_query

#  Answer Generation 
class FinalAnswerSignature(dspy.Signature):
    """Answer questions based on context from the knowledge base and the conversation history."""
    
    context: List[str] = dspy.InputField(desc="Relevant documents from the knowledge base.")
    question: str = dspy.InputField(desc="The user's original, unmodified question.")
    chat_history: str = dspy.InputField(desc="Recent conversation history for context.")
    answer: str = dspy.OutputField(desc="A comprehensive and accurate answer based ONLY on the provided context.")

# TODO: This is where business requirements come into play.
# The strictness of Answer ONLY on the context removes some of the capabilities of the LLM.
# I'm thinking hallucination detection might be better and give it more freedom. (e.g. LettuceDetect)
# I've been working on GEPA + NLI -> dspy.Refine + NLI, but it's not ready for this project. Still working on CrossingGuard dataset w/ Lee

# GEPA is essentially designed to introspect why it got a score.
# NLI provides score (entailment probability) as well as textual feedback.
# So the prompts/modules evolve across your search space in GEPA + NLI, and then Refine+NLI takes the specific failing(?) examples and explicitly refines then
# So if you can express any evaluation criteria with natural language, you now have a universal optimizer. You could potentially skip writing reward functions almost? Since it's textual. 
# This might be really good 'research' approach for determining best ways to prompt for specific tasks then too.


FinalAnswerSignature.__doc__ = """You are a helpful and knowledgeable AI assistant.
CRITICAL RULES:
1. Answer ONLY based on the `context` provided. If the context does not contain the answer, state that clearly. Do not use outside knowledge.
2. Use the `chat_history` to understand pronouns (like 'it', 'they') and follow-up questions.
3. Reference the source of your information, e.g., 'According to [Source: file.pdf, Page: 3], ...'
4. Be precise and accurate. If the context is insufficient, explicitly state that."""

class RAG(dspy.Module):
    """A RAG program with a dedicated query understanding engine."""
    
    def __init__(self, k: int = 5) -> None:
        super().__init__()
        self.query_engine = QueryUnderstandingEngine()
        self.generate_answer = dspy.ChainOfThought(FinalAnswerSignature)
        self.k = k
    
    async def aforward(self, question: str, chat_history: str):
        """The main forward pass for the RAG program."""
        
        #  Understand Query: Use the engine to create a search query
        async with cl.Step(name="Understanding Query") as step:
            search_query = await self.query_engine.aforward(question, chat_history)
            step.output = f"**Synthesized Search Query:**\n\n```\n{search_query}\n```"

        # Retrieve Documents: Use the synthesized query to find context
        async with cl.Step(name="Retrieving Documents") as step:
            retrieved_docs = await retrieve_from_postgres(search_query, k=self.k)
            step.output = "\n\n---\n\n".join([f"**Source:** {d['source']}, **Page:** {d['page']}, **Similarity:** {d['similarity']:.3f}" for d in retrieved_docs])
        
        # 3. Handle No Context: If no documents are found, provide a graceful response.
        if not retrieved_docs:
            logger.warning("No relevant documents found for the synthesized query.")
            return dspy.Prediction(answer="I couldn't find any information about that in my knowledge base. Could you try asking in a different way?")
        
        # 4. Generate Final Answer: Use the retrieved docs to answer the ORIGINAL question.
        context_passages = [f"[Source: {doc['source']}, Page: {doc['page']}]\n{doc['content']}" for doc in retrieved_docs]
        
        async with cl.Step(name="Generating Answer") as step:
            prediction = await self.generate_answer.acall(
                context=context_passages,
                question=question, # CRITICAL: Use the original question for the final answer
                chat_history=chat_history
            )
            step.output = prediction.answer
        
        logger.info(f"Answer generated (length: {len(prediction.answer)} chars)")
        return prediction


# CHAINLIT UI AND APPLICATION LOGIC 
# TODO: refactor to modular code. 
# tree building technique based on topic expansion
# HyDE good for large db
# was having trouble with context across turns, this is the solution, fits Option2

@cl.on_chat_start
async def start_chat():
    """Initializes the user session when a new chat begins."""
    # Initialize Redis client for this session
    redis_client = redis.Redis(
        host=settings.redis_host, 
        port=settings.redis_port, 
        decode_responses=True
    )
    history_manager = RedisChatMessageHistory(
        session_id=cl.user_session.get("id"), 
        redis_client=redis_client,
        ttl=settings.redis_ttl
    )
    rag_program = RAG(k=settings.rag_k)
    
    cl.user_session.set("history_manager", history_manager)
    cl.user_session.set("rag_program", rag_program)
    
    await cl.Message(
        content="Hello! I'm here to help answer questions based on my knowledge base. How may I assist you?"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handles incoming user messages with the RAG pipeline."""
    logger.info(f"Received message: '{message.content}'")
    
    rag_program: RAG = cl.user_session.get("rag_program")
    history_manager: RedisChatMessageHistory = cl.user_session.get("history_manager")
    
    messages = await history_manager.get_messages(limit=settings.chat_history_limit)

    # Format the history into a string for dspy program...maybe I should just make the type hint List[Dict] and remove this?
    formatted_history = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
    logger.info(f"Chat history has {len(messages)} messages")
    
    # Create an empty message to stream the response into?
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        prediction = await rag_program.aforward(
            question=message.content,
            chat_history=formatted_history
        )
        final_answer = prediction.answer
        
        await msg.stream_token(final_answer)
        
        await history_manager.add_message(ChatMessage(role="user", content=message.content))
        await history_manager.add_message(ChatMessage(role="assistant", content=final_answer))
        
        logger.info("Message processing complete")
        
    except Exception as e:
        error_msg = f"An error occurred while processing your request. Please try again."
        await msg.stream_token(error_msg)
        logger.error(f"FATAL Error in RAG pipeline: {e}", exc_info=True)
    
    await msg.update()