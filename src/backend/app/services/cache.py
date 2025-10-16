import json
from typing import List
import redis.asyncio as redis
from app.models.chat import ChatMessage
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisChatMessageHistory:
    """Manages chat history in Redis."""
    
    def __init__(self, session_id: str, redis_client: redis.Redis, ttl: int):
        self.redis_client = redis_client
        self.session_id = session_id
        self.key = f"chat_history:{self.session_id}"
        self.ttl = ttl

    async def add_message(self, message: ChatMessage) -> None:
        """Adds a new message to the history."""
        await self.redis_client.rpush(self.key, message.model_dump_json())
        await self.redis_client.expire(self.key, self.ttl)

    async def get_messages(self, limit: int = 20) -> List[ChatMessage]:
        """Retrieve the last N messages from the history."""
        raw_messages = await self.redis_client.lrange(self.key, -limit, -1)
        
        messages = []
        for raw_msg in raw_messages:
            msg_dict = json.loads(raw_msg)
            messages.append(ChatMessage.model_validate(msg_dict))
                
        return messages
        
    async def clear(self) -> None:
        """Clears the chat history for the session."""
        await self.redis_client.delete(self.key)