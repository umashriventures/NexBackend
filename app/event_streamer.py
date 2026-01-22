from pydantic import BaseModel
import json
from typing import Any, Dict

class PartialTranscriptEvent(BaseModel):
    type: str = "partial_transcript"
    text: str

class FinalTranscriptEvent(BaseModel):
    type: str = "final_transcript"
    text: str

class LLMTokenEvent(BaseModel):
    type: str = "llm_token"
    token: str

class StatusUpdateEvent(BaseModel):
    type: str = "status_update"
    status: str

class ErrorEvent(BaseModel):
    type: str = "error"
    message: str

def serialize_event(event: BaseModel) -> str:
    """Serialize a Pydantic event model to JSON string for WebSocket transmission."""
    return json.dumps(event.dict())
