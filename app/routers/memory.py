from fastapi import APIRouter, Depends, HTTPException
from ..auth_service import get_current_user_id
from ..memory_service import memory_service
from ..user_service import user_service
from ..models import MemoryListResponse, CreateMemoryRequest, CreateMemoryResponse, ErrorResponse, TIER_LIMITS, UpdateMemoryRequest, DeleteMemoryResponse, MemoryItem

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

@router.get("/{memory_id}", response_model=MemoryItem)
async def get_memory(memory_id: str, uid: str = Depends(get_current_user_id)):
    item = await memory_service.get_memory(uid, memory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Memory not found")
    return item

@router.put("/{memory_id}")
async def update_memory(memory_id: str, req: UpdateMemoryRequest, uid: str = Depends(get_current_user_id)):
    success = await memory_service.update_memory(uid, memory_id, req.content)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or update failed")
    
    return {"status": "UPDATED"}

@router.delete("/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(memory_id: str, uid: str = Depends(get_current_user_id)):
    success = await memory_service.delete_memory(uid, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # Get user state to return remaining
    user_state = await user_service.get_user_state(uid)
    limit = TIER_LIMITS[user_state.tier]["memory"]
    remaining = limit - user_state.memory_used if limit != float('inf') else float('inf')
    
    return DeleteMemoryResponse(
        status="DELETED",
        memory_remaining=remaining
    )
