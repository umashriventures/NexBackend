from fastapi import APIRouter, Depends, HTTPException
from ..auth_service import get_current_user_id
from ..nex_service import nex_service
from ..user_service import user_service
from ..models import InteractionRequest, InteractionResponse, ErrorResponse, TIER_LIMITS, Tier

router = APIRouter(prefix="/nex", tags=["NEX"])

@router.post("/interact", response_model=InteractionResponse | ErrorResponse)
async def interact(req: InteractionRequest, uid: str = Depends(get_current_user_id)):
    # req.session_id is now required in InteractionRequest
    reply, tier = await nex_service.interact(uid, req.session_id, req.input)
    
    if reply == "SESSION_INVALID":
        raise HTTPException(status_code=400, detail="Invalid Session. Please start a new session.")

    if reply == "LIMIT_REACHED":
        return ErrorResponse(
            error="MESSAGE_LIMIT_REACHED",
            tier=tier,
            upgrade_available=True
        )

    if reply == "RATE_LIMITED":
        raise HTTPException(
            status_code=429,
            detail="AI Service is currently overloaded. Please try again later."
        )
    
    if reply == "ERROR":
        raise HTTPException(status_code=500, detail="AI Interaction Failed")

    user_state = await user_service.get_user_state(uid)
    limit = TIER_LIMITS[tier]["messages"]
    remaining = limit - user_state.messages_used_today if limit != float('inf') else float('inf')

    return InteractionResponse(
        reply=reply,
        messages_remaining=remaining,
        tier=tier
    )