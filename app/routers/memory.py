from fastapi import APIRouter, Depends, HTTPException
from ..auth_service import get_current_user_id
from ..memory_service import memory_service
from ..user_service import user_service
from ..models import MemoryListResponse, CreateMemoryRequest, CreateMemoryResponse, ErrorResponse, TIER_LIMITS

router = APIRouter(prefix="/memory", tags=["Memory"])

@router.get("", response_model=MemoryListResponse)
async def list_memories(uid: str = Depends(get_current_user_id)):
    user_state = await user_service.get_user_state(uid)
    return await memory_service.list_memories(uid, user_state.tier, user_state.memory_used)

@router.post("")
async def create_memory(req: CreateMemoryRequest, uid: str = Depends(get_current_user_id)):
    user_state = await user_service.get_user_state(uid)
    limit = TIER_LIMITS[user_state.tier]["memory"]
    
    if user_state.memory_used >= limit:
        return ErrorResponse(
            error="MEMORY_LIMIT_REACHED",
            tier=user_state.tier,
            upgrade_available=True
        )
    
    await memory_service.add_memory(uid, req.content)
    
    limit = TIER_LIMITS[user_state.tier]["memory"]
    remaining = limit - (user_state.memory_used + 1) if limit != float('inf') else float('inf')
    
    return CreateMemoryResponse(
        status="SAVED",
        memory_remaining=remaining
    )
