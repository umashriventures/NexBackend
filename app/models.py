from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Tier(str, Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"

TIER_LIMITS = {
    Tier.TIER_1: {"messages": 20, "memory": 5},
    Tier.TIER_2: {"messages": 50, "memory": 20},
    Tier.TIER_3: {"messages": float('inf'), "memory": float('inf')}
}

class UserState(BaseModel):
    uid: str
    tier: Tier
    messages_used_today: int
    daily_limit: int | float
    memory_used: int
    memory_limit: int | float

class InteractionRequest(BaseModel):
    input: str

class InteractionResponse(BaseModel):
    reply: str
    messages_remaining_today: int | float
    tier: Tier

class ErrorResponse(BaseModel):
    error: str
    tier: Tier
    upgrade_available: bool

class MemoryItem(BaseModel):
    id: str
    content: str
    created_at: str

class MemoryListResponse(BaseModel):
    memory_limit: int | float
    memory_used: int
    items: List[MemoryItem]

class CreateMemoryRequest(BaseModel):
    content: str

class CreateMemoryResponse(BaseModel):
    status: str
    memory_remaining: int | float

class SubscriptionStatusResponse(BaseModel):
    tier: Tier
    daily_limit: int | float
    memory_limit: int | float

class UpgradeSubscriptionRequest(BaseModel):
    new_tier: Tier
    subscription_expiry: Optional[str] = None
