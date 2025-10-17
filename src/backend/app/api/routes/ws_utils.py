import json
from typing import List, Dict, Any
from app.dependencies.websocket import ConnectionManager
from app.models.chat import WSMessage


async def send_start(manager: ConnectionManager, session_id: str):
    """Send start message to client."""
    await manager.send_message(
        session_id,
        WSMessage(type="start", content="Processing...", session_id=session_id),
    )


async def send_step(
    manager: ConnectionManager, session_id: str, content: str, step_name: str
):
    """Send step progress message to client."""
    await manager.send_message(
        session_id, WSMessage(type="step", content=content, step_name=step_name)
    )


async def send_tokens(manager: ConnectionManager, session_id: str, text: str):
    """Stream text as word tokens to client."""
    words = text.split()
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        await manager.send_message(session_id, WSMessage(type="token", content=token))


async def send_end(
    manager: ConnectionManager,
    session_id: str,
    retrieved_docs: List[Dict[str, Any]],
    search_query: str,
):
    """Send completion message to client."""
    await manager.send_message(
        session_id,
        WSMessage(
            type="end",
            content=json.dumps(
                {"retrieved_docs": retrieved_docs, "search_query": search_query}
            ),
            session_id=session_id,
        ),
    )


async def send_error(manager: ConnectionManager, session_id: str, error_msg: str):
    """Send error message to client."""
    await manager.send_message(session_id, WSMessage(type="error", content=error_msg))
