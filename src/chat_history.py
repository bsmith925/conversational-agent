import uuid
from datetime import datetime, timezone
from typing import List, Literal
import json 
import redis.asyncio as redis
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chainlit chat message."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Later support for artifacts (or references to them)

class RedisChatMessageHistory:
    """Manages chat history in Redis. Its sole responsibility is storing and retrieving ChatMessage objects."""
    def __init__(self, session_id: str, redis_client: redis.Redis, ttl: int = 3600) -> None:
        self.redis_client = redis_client
        self.session_id = session_id
        self.key = f"chat_history:{self.session_id}"
        self.ttl = ttl

    async def add_message(self, message: ChatMessage):
        """Adds a new message to the history."""
        await self.redis_client.rpush(self.key, message.model_dump_json())
        # refresh expiry
        await self.redis_client.expire(self.key, self.ttl)

    async def get_messages(self, limit: int = 20) -> List[ChatMessage]:
        """Retrieve messages from the history."""
        # Get the last `limit` messages. LRANGE key start stop. -limit to -1 gets the last N items.
        raw_messages = await self.redis_client.lrange(self.key, -limit, -1)
        
        messages = []
        for raw_msg in raw_messages:
            # If raw_msg is already a string (decode_responses=True), no need to decode
            msg_dict = json.loads(raw_msg)
            messages.append(ChatMessage.model_validate(msg_dict))
                
        return messages

    

    # Maybe end up storing the documents we did RAG on with the message?
    #  add a field `retrieved_context: Optional[List[Dict]] = None`
    #  to the ChatMessage model and store it with the assistant's message for traceability.
        
    async def clear(self):
        """Clears the chat history for the session."""
        await self.redis_client.delete(self.key)
    
    # TODO: other helpers