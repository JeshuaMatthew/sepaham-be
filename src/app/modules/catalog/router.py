from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser, FacultyUser
from src.app.modules.catalog import service
from src.app.modules.catalog.schemas import (
    RolesResponse,
    InternshipsResponse,
    AiFeedResponse,
    LofiTracksResponse,
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)

router = APIRouter(prefix="/api", tags=["Catalog"])

@router.get("/roles", response_model=RolesResponse, status_code=status.HTTP_200_OK)
async def get_roles(db: AsyncSession = Depends(get_db)):
    return await service.get_roles(db)

# Catatan: endpoint `/api/onboarding/questions` versi Likert lama sudah dihapus.
# Endpoint itu men-shadow router onboarding (path-nya identik) dan mengembalikan
# bentuk `{id, text, roleId}` yang tidak punya fact_id, sehingga mahasiswa tidak
# pernah melihat hasil suntingan dosen di sana. Bank soal yang benar dikelola
# lewat modul onboarding: `/questions?pillar=` untuk mahasiswa, serta
# `/questions/bank` + `PUT /questions` (khusus faculty) untuk editor soal.

@router.get("/badges", status_code=status.HTTP_200_OK)
async def get_badges_catalog(db: AsyncSession = Depends(get_db)):
    return await service.get_badges_catalog(db)

@router.get("/internships/contacts", response_model=InternshipsResponse, status_code=status.HTTP_200_OK)
async def get_internships(db: AsyncSession = Depends(get_db)):
    return await service.get_internships(db)

@router.get("/ai/feed", response_model=AiFeedResponse, status_code=status.HTTP_200_OK)
async def get_ai_feed(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_ai_feed(db, user.id)

@router.get("/music/lofi", response_model=LofiTracksResponse, status_code=status.HTTP_200_OK)
async def get_lofi(db: AsyncSession = Depends(get_db)):
    return await service.get_lofi(db)

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
