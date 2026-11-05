from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import FacultyUser
from src.app.modules.roadmap import service
from src.app.modules.roadmap.schemas import (
    RoadmapsListResponse,
    RoadmapDetailResponse,
    RoadmapUpsertRequest,
)

router = APIRouter(prefix="/api", tags=["Roadmap"])

@router.get("/roadmaps", response_model=RoadmapsListResponse, status_code=status.HTTP_200_OK)
async def get_roadmaps(db: AsyncSession = Depends(get_db)):
    return await service.get_roadmaps(db)

@router.get("/roadmaps/{id}", response_model=RoadmapDetailResponse, status_code=status.HTTP_200_OK)
async def get_roadmap_detail(id: str, db: AsyncSession = Depends(get_db)):
    return await service.get_roadmap_detail(db, id)

@router.put("/roadmaps/{id}", status_code=status.HTTP_200_OK)
async def upsert_roadmap(
    id: str,
    req: RoadmapUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.upsert_roadmap(db, id, req, faculty.id)

@router.post("/roadmaps", status_code=status.HTTP_201_CREATED)
async def create_roadmap(
    req: RoadmapUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Buat roadmap baru. Id dibuat server."""
    return await service.create_roadmap(db, req, faculty.id)

@router.delete("/roadmaps/{id}", status_code=status.HTTP_200_OK)
async def delete_roadmap(
    id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.delete_roadmap(db, id)

@router.get(
    "/faculty/roadmaps/{id}",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_faculty_roadmap_detail(
    id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Roadmap detail khusus faculty."""
    return await service.get_roadmap_detail(db, id)
