import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.cache import RedisChatMessageHistory
from app.models.chat import ChatMessage, WSMessage
from app.dependencies.cache import get_redis_client
from app.dependencies.vector_db import get_vector_database, get_embedding_model
from app.dependencies.rag import get_rag_service
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# TODO: move this into a websocket dependency.
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
##
    async def send_message(self, session_id: str, message: WSMessage):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(
                    message.model_dump_json()
                )
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                raise

# TODO: move with dep. 
manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for streaming chat responses - persistent connection."""
    await manager.connect(session_id, websocket)

    # Initialize dependencies once for this connection
    # TODO: move these to use Depends(Annotated[type, fnc])
    redis_client = await get_redis_client()
    embedding_model = get_embedding_model()
    vector_db = get_vector_database(embedding_model)
    rag_service = get_rag_service(vector_db)

    history_manager = RedisChatMessageHistory(
        session_id=session_id,
        redis_client=redis_client,
        ttl=settings.redis_ttl
    )

    try:
        # Keeping websocket alive..still not sure I've done ws right
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            logger.info(f"Received message from {session_id}: {user_message[:100]}")

            # Send start message
            await manager.send_message(
                session_id,
                WSMessage(type="start", content="Processing...", session_id=session_id)
            )

            try:
                # Get chat history
                messages = await history_manager.get_messages(
                    limit=settings.chat_history_limit
                )
                formatted_history = "\n".join(
                    [f"{msg.role}: {msg.content}" for msg in messages]
                )

                logger.info(f"Chat history has {len(messages)} messages")

                # Send step: Understanding query
                await manager.send_message(
                    session_id,
                    WSMessage(
                        type="step",
                        content="Understanding your question...",
                        step_name="query_understanding"
                    )
                )

                # Process through RAG
                result = await rag_service.process_query(
                    question=user_message,
                    chat_history=formatted_history
                )

                # Send step: Documents retrieved
                await manager.send_message(
                    session_id,
                    WSMessage(
                        type="step",
                        content=f"Retrieved {len(result.retrieved_docs)} documents",
                        step_name="retrieval"
                    )
                )
                
                await manager.send_message(
                    session_id,
                    WSMessage(
                        type="step",
                        content="Generating answer...",
                        step_name="generation"
                    )
                )
                
                words = result.answer.split()
                for i, word in enumerate(words):
                    token = word if i == 0 else f" {word}"
                    await manager.send_message(
                        session_id,
                        WSMessage(type="token", content=token)
                    )
                
                await manager.send_message(
                    session_id,
                    WSMessage(
                        type="end",
                        content=json.dumps({
                            "retrieved_docs": [
                                doc.model_dump() for doc in result.retrieved_docs
                            ],
                            "search_query": result.search_query
                        }),
                        session_id=session_id
                    )
                )
                
                await history_manager.add_message(
                    ChatMessage(role="user", content=user_message)
                )
                await history_manager.add_message(
                    ChatMessage(
                        role="assistant",
                        content=result.answer,
                        retrieved_context=[
                            doc.model_dump() for doc in result.retrieved_docs
                        ]
                    )
                )

                logger.info(f"Message processing complete for {session_id}")

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                error_content = f"An error occurred while processing your request: {str(e)}"
                
                # Send the error message to the client
                await manager.send_message(
                    session_id,
                    WSMessage(
                        type="error",
                        content=error_content
                    )
                )
                
                # Close the connection with an error code (1011 = Internal Error)
                # makes the server's state more predictable.
                await websocket.close(code=1011, reason="Internal Server Error during processing")
                
                # Break the loop since the connection will be closed
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
        # Ensure disconnection if an error happens outside the inner loop
        manager.disconnect(session_id)