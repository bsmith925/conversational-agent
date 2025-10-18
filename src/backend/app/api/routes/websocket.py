import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.dependencies.websocket import ConnectionManagerDep
from app.dependencies.chat import get_chat_service
from app.services.chat import ChatService
from app.api.routes.ws_utils import (
    send_start,
    send_step,
    send_tokens,
    send_end,
    send_error,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: ConnectionManagerDep,
    chat_service: ChatService = Depends(get_chat_service),
):
    """WebSocket endpoint for streaming chat responses - persistent connection."""
    try:
        await manager.connect(session_id, websocket)
    except Exception as e:
        logger.error(
            f"Failed to connect WebSocket for {session_id}: {e}", exc_info=True
        )
        await websocket.close(code=1011, reason="Connection failed")
        return

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            logger.info(f"Received message from {session_id}: {user_message[:100]}")

            # Send start message
            await send_start(manager, session_id)

            try:
                # Send step: Understanding query
                await send_step(
                    manager,
                    session_id,
                    "Understanding your question...",
                    "query_understanding",
                )

                # Process through ChatService
                result = await chat_service.process_message(user_message, session_id)

                # Send step: Documents retrieved
                await send_step(
                    manager,
                    session_id,
                    f"Retrieved {len(result.retrieved_docs)} documents",
                    "retrieval",
                )

                await send_step(
                    manager, session_id, "Generating answer...", "generation"
                )

                # Stream the response
                await send_tokens(manager, session_id, result.answer)

                # Send completion
                await send_end(
                    manager,
                    session_id,
                    [doc.model_dump() for doc in result.retrieved_docs],
                    result.search_query,
                )

                logger.info(f"Message processing complete for {session_id}")

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                error_content = (
                    f"An error occurred while processing your request: {str(e)}"
                )

                # Send the error message to the client
                await send_error(manager, session_id, error_content)

                # Close the connection with an error code (1011 = Internal Error)
                await websocket.close(
                    code=1011, reason="Internal Server Error during processing"
                )
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
        manager.disconnect(session_id)
