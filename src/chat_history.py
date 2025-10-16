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
    # Later support for artifacts

class RedisChatMessageHistory:
    """Manages chat history in Redis."""
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
        raw_messages = await self.redis_client.lrange(self.key, 0, -1)
        
        messages = []
        for raw_msg in raw_messages:
            # If raw_msg is already a string (decode_responses=True)
            if isinstance(raw_msg, str):
                msg_dict = json.loads(raw_msg)
            else:
                # If raw_msg is bytes
                msg_dict = json.loads(raw_msg.decode('utf-8'))
            
            messages.append(ChatMessage.model_validate(msg_dict))
                
        return messages

    # I want this associated with a program, not here. And accepts list of messages
    async def get_formatted_string(self) -> str:
        """Get the chat history as a formatted string."""
        messages = await self.get_messages()
        
        if not messages:
            return ""
        
        return "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
    
    # Maybe end up storing the documents we did RAG on with the message?
        

    async def clear(self):
        """Clears the chat history for the session."""
        await self.redis_client.delete(self.key)
    
    # TODO: other helpers