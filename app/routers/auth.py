from fastapi import APIRouter, Depends, Header
from ..auth_service import get_current_user_id
from ..user_service import user_service
from ..models import UserState
from firebase_admin import auth

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/bootstrap", response_model=UserState)
async def bootstrap(uid: str = Depends(get_current_user_id)):
    """
    Bootstrap user record and return state.
    """
    # Fetch email from firebase auth directly since we have the token verified
    user_record = auth.get_user(uid)
    return await user_service.bootstrap_user(uid, email=user_record.email)
