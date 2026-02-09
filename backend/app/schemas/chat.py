from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None)
    message: str
    image_text: Optional[str] = None
    image_answer: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    disclaimer: str
    urgent_notice: Optional[str] = None
    red_flag: bool = False
    citations: List[Any] = Field(default_factory=list)
    rag_context: Optional[str] = None


class IngestRequest(BaseModel):
    text: str
    metadata: Optional[dict[str, Any]] = None
