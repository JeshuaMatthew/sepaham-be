from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.profile.schemas import ProfileResponse, ProfileUpdateRequest, CVResponse, BadgeItem
from src.app.modules.profile import service

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def get_profile(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_profile(db, user.id)

@router.put("", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def update_profile(req: ProfileUpdateRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.update_profile(db, user.id, req)

@router.post("/cv", response_model=CVResponse, status_code=status.HTTP_200_OK)
async def upload_cv(file: UploadFile = File(...), user: CurrentUser = None, db: AsyncSession = Depends(get_db)):
    return await service.upload_cv(db, user.id, file)

@router.delete("/cv", status_code=status.HTTP_200_OK)
async def delete_cv(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.delete_cv(db, user.id)

@router.get("/badges", response_model=list[BadgeItem], status_code=status.HTTP_200_OK)
async def get_badges(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_badges(db, user.id)
