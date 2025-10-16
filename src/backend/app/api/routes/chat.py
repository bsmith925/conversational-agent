import uuid
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.cache import RedisChatMessageHistory
from app.models.chat import ChatMessage
from app.dependencies.cache import RedisClient
from app.dependencies.rag import RAGDep
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    redis_client: RedisClient,
    rag_service: RAGDep
):
    """
    Process a chat message and return a response.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    logger.info(f"Processing message for session: {session_id}")
    
    try:
        history_manager = RedisChatMessageHistory(
            session_id=session_id,
            redis_client=redis_client,
            ttl=settings.redis_ttl
        )

        messages = await history_manager.get_messages(limit=settings.chat_history_limit)
        formatted_history = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        
        logger.info(f"Chat history has {len(messages)} messages")
        
        result = await rag_service.process_query(
            question=request.message,
            chat_history=formatted_history
        )
        
        await history_manager.add_message(
            ChatMessage(role="user", content=request.message)
        )
        await history_manager.add_message(
            ChatMessage(
                role="assistant",
                content=result.answer,
                retrieved_context=[doc.model_dump() for doc in result.retrieved_docs]
            )
        )
        
        logger.info("Message processing complete")
        
        return ChatResponse(
            answer=result.answer,
            session_id=session_id,
            retrieved_docs=[doc.model_dump() for doc in result.retrieved_docs]
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request."
        )


@router.delete("/{session_id}")
async def clear_history(
    session_id: str,
    redis_client: RedisClient
):
    """Clear chat history for a session."""
    history_manager = RedisChatMessageHistory(
        session_id=session_id,
        redis_client=redis_client,
        ttl=settings.redis_ttl
    )
    await history_manager.clear()
    
    return {"message": f"Chat history cleared for session {session_id}"}