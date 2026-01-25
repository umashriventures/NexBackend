from pydantic import BaseModel
from typing import Optional

class RoutingDecision(BaseModel):
    needs_past_memory: bool
    standalone_answer: Optional[str] = None
    memory_one_liner: Optional[str] = None
    reasoning: str
