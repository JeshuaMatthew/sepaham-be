from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.catalog import service
from src.app.modules.catalog.schemas import (
    RolesResponse,
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)

router = APIRouter(prefix="/api", tags=["Catalog"])

@router.get("/roles", response_model=RolesResponse, status_code=status.HTTP_200_OK)
async def get_roles(db: AsyncSession = Depends(get_db)):
    return await service.get_roles(db)

@router.get("/preferences", response_model=Optional[UserPreferenceResponse], status_code=status.HTTP_200_OK)
async def get_preferences(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_preferences(db, user.id)

@router.put("/preferences", response_model=UserPreferenceResponse, status_code=status.HTTP_200_OK)
async def upsert_preferences(
    req: UserPreferenceUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.upsert_preferences(db, user.id, req)
