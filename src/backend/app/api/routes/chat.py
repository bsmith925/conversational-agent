import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models.chat import ChatRequest, ChatResponse
from app.dependencies.chat import get_chat_service
from app.services.chat import ChatService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    Process a chat message and return a response.
    """
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Processing message for session: {session_id}")

    try:
        result = await chat_service.process_message(request.message, session_id)

        return ChatResponse(
            answer=result.answer,
            session_id=session_id,
            retrieved_docs=[doc.model_dump() for doc in result.retrieved_docs],
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred while processing your request."
        )


@router.delete("/{session_id}")
async def clear_history(
    session_id: str, chat_service: ChatService = Depends(get_chat_service)
):
    """Clear chat history for a session."""
    await chat_service.cache.clear(session_id)

    return {"message": f"Chat history cleared for session {session_id}"}
