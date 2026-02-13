from fastapi import APIRouter, Depends, HTTPException, Body
from ..auth_service import get_current_user_id
from ..session_service import session_service
from ..archive_service import archive_service
from ..models import SessionStartResponse, SessionEndResponse, Archive, ErrorResponse, Tier
from typing import List
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/session", tags=["Session"])
archive_router = APIRouter(prefix="/archive", tags=["Archive"])

@router.post("/start", response_model=SessionStartResponse)
async def start_session(uid: str = Depends(get_current_user_id)):
    session, error = await session_service.start_session(uid)
    if error:
        if error == "DAILY_SESSION_LIMIT_REACHED":
            raise HTTPException(status_code=403, detail="Daily session limit reached for your tier.")
        raise HTTPException(status_code=400, detail=error)
    
    return SessionStartResponse(session_id=session.session_id, message="Session started successfully")

@router.post("/end", response_model=SessionEndResponse)
async def end_session(session_id: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    # Verify ownership
    active = await session_service.get_active_session(uid)
    
    if not active or active.session_id != session_id:
         raise HTTPException(status_code=404, detail="Active session not found or invalid session ID")

    archive_data = await session_service.end_session(session_id)
    if not archive_data:
        raise HTTPException(status_code=500, detail="Failed to end session")
        
    return SessionEndResponse(**archive_data)

@archive_router.get("/", response_model=List[Archive])
async def get_user_archives(uid: str = Depends(get_current_user_id)):
    return await archive_service.get_user_archives(uid)

@archive_router.get("/{archive_id}", response_model=Archive)
async def get_archive(archive_id: str, uid: str = Depends(get_current_user_id)):
    archive = await archive_service.get_archive(archive_id)
    if not archive or archive.user_id != uid:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive

@archive_router.post("/{archive_id}/download")
async def download_archive(archive_id: str, uid: str = Depends(get_current_user_id)):
    archive = await archive_service.get_archive(archive_id)
    if not archive or archive.user_id != uid:
        raise HTTPException(status_code=404, detail="Archive not found")
        
    img_io = archive_service.generate_archive_image(archive)
    return StreamingResponse(img_io, media_type="image/png")
