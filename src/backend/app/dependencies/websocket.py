from typing import Annotated
from functools import lru_cache
from fastapi import Depends, WebSocket
from app.models.chat import WSMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


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

    async def send_message(self, session_id: str, message: WSMessage):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(
                    message.model_dump_json()
                )
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                raise


@lru_cache(maxsize=1)
def get_connection_manager() -> ConnectionManager:
    """Dependency that provides a ConnectionManager singleton."""
    logger.info("ConnectionManager initialized")
    return ConnectionManager()


# Type alias for dependency injection
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
