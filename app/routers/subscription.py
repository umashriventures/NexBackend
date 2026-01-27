from fastapi import APIRouter, Depends
from ..auth_service import get_current_user_id
from ..user_service import user_service
from ..models import SubscriptionStatusResponse, UpgradeSubscriptionRequest, TIER_LIMITS

router = APIRouter(prefix="/subscription", tags=["Subscription"])

@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_status(uid: str = Depends(get_current_user_id)):
    user_state = await user_service.get_user_state(uid)
    return SubscriptionStatusResponse(
        tier=user_state.tier,
        daily_limit=user_state.daily_limit,
        memory_limit=user_state.memory_limit
    )

@router.post("/upgrade")
async def upgrade(req: UpgradeSubscriptionRequest, uid: str = Depends(get_current_user_id)):
    # In a real app, verify internal secret or payment success here
    await user_service.update_tier(uid, req.new_tier, req.subscription_expiry)
    return {
        "status": "ACTIVE",
        "tier": req.new_tier
    }
