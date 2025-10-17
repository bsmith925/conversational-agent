import uuid
from datetime import datetime, timezone
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retrieved_context: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(default=None)


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str
    session_id: str
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)


class WSMessage(BaseModel):
    """WebSocket message format."""

    type: Literal["start", "token", "step", "end", "error"]
    content: str
    step_name: Optional[str] = None
    session_id: Optional[str] = None
