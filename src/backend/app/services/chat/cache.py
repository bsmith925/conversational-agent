import json
from typing import List
from app.database import RedisDatabase
from app.models.chat import ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatCache:
    """Chat-specific cache operations using Redis infrastructure."""

    def __init__(self, redis_db: RedisDatabase, ttl: int = 3600):
        self.redis_db = redis_db
        self.ttl = ttl

    def _get_chat_key(self, session_id: str) -> str:
        """Get the Redis key for a chat session."""
        return f"chat_history:{session_id}"

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to chat history."""
        key = self._get_chat_key(session_id)
        await self.redis_db.lpush(key, message.model_dump_json())
        await self.redis_db.expire(key, self.ttl)

    async def get_messages(self, session_id: str, limit: int = 20) -> List[ChatMessage]:
        """Get chat messages for a session."""
        key = self._get_chat_key(session_id)
        raw_messages = await self.redis_db.lrange(key, -limit, -1)

        messages = []
        for raw_msg in raw_messages:
            msg_dict = json.loads(raw_msg)
            messages.append(ChatMessage.model_validate(msg_dict))

        return messages

    async def clear(self, session_id: str) -> None:
        """Clear the chat history for the session."""
        key = self._get_chat_key(session_id)
        await self.redis_db.delete(key)
