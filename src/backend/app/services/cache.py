import json
from typing import List
import redis.asyncio as redis
from app.models.chat import ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisChatMessageHistory:
    """Manages chat history in Redis."""

    def __init__(self, redis_client: redis.Redis, ttl: int):
        self.redis_client = redis_client
        self.ttl = ttl

    def _get_key(self, session_id: str) -> str:
        """Get the Redis key for a session."""
        return f"chat_history:{session_id}"

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Adds a new message to the history."""
        key = self._get_key(session_id)
        await self.redis_client.rpush(key, message.model_dump_json())
        await self.redis_client.expire(key, self.ttl)

    async def get_messages(self, session_id: str, limit: int = 20) -> List[ChatMessage]:
        """Retrieve the last N messages from the history."""
        key = self._get_key(session_id)
        raw_messages = await self.redis_client.lrange(key, -limit, -1)

        messages = []
        for raw_msg in raw_messages:
            msg_dict = json.loads(raw_msg)
            messages.append(ChatMessage.model_validate(msg_dict))

        return messages

    async def clear(self, session_id: str) -> None:
        """Clears the chat history for the session."""
        key = self._get_key(session_id)
        await self.redis_client.delete(key)
