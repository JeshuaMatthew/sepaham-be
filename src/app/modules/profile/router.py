from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.profile.schemas import ProfileResponse, ProfileUpdateRequest
from src.app.modules.profile import service

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def get_profile(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_profile(db, user.id)

@router.put("", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def update_profile(req: ProfileUpdateRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.update_profile(db, user.id, req)
