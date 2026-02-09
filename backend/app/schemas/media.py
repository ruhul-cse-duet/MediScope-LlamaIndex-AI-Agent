from __future__ import annotations

from pydantic import BaseModel


class TtsRequest(BaseModel):
    text: str


class SttResponse(BaseModel):
    text: str


class VisionResponse(BaseModel):
    ocr_text: str
    answer: str | None = None
