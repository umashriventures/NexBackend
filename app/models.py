from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

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
    session_id: str = Field(..., description="Active session ID required")

class InteractionResponse(BaseModel):
    reply: str
    messages_remaining: int | float
    tier: Tier

class ErrorResponse(BaseModel):
    error: str
    tier: Tier
    upgrade_available: bool

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    session_id: str
    user_id: str
    started_at: datetime
    last_message_at: datetime
    is_active: bool
    message_count: int
    transcript: List[Message] = []

class Archive(BaseModel):
    archive_id: str
    user_id: str
    title: str
    reflection: str
    emotion_tag: str
    created_at: datetime

class SessionStartResponse(BaseModel):
    session_id: str
    message: str

class SessionEndResponse(BaseModel):
    archive_id: str
    title: str
    reflection: str
    emotion_tag: str

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

class UpdateMemoryRequest(BaseModel):
    content: str

class DeleteMemoryResponse(BaseModel):
    status: str
    memory_remaining: int | float

class CreateOrderRequest(BaseModel):
    planId: Tier
    currency: str = "INR"

class CreateOrderResponse(BaseModel):
    id: str
    currency: str
    amount: int
    keyId: str

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class VerifyPaymentResponse(BaseModel):
    status: str
    tier: Tier
    updatedAt: datetime
