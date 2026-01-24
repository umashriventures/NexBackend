from pydantic import BaseModel, Field
from typing import List, Optional

class BeliefState(BaseModel):
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    ambiguities: List[str] = []
    assumptions: List[str] = []
    requires_context: bool = False

class Intent(BaseModel):
    category: str
    requires_memory: bool
    confidence: float

class CognitiveState(BaseModel):
    belief: BeliefState
    intent: Optional[Intent] = None
    transcript: str
