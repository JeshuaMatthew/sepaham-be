from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser, FacultyUser
from src.app.modules.roadmap import service
from src.app.modules.roadmap.schemas import (
    RoadmapsListResponse,
    RoadmapDetailResponse,
    RoadmapUpsertRequest,
    SubmissionState,
    SubmissionUpsertRequest,
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

@router.get("/roadmaps/{id}/submissions", response_model=dict[str, SubmissionState], status_code=status.HTTP_200_OK)
async def get_submissions(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_submissions(db, user.id, id)

@router.put("/roadmaps/{id}/nodes/{node_key}/submission", response_model=SubmissionState, status_code=status.HTTP_200_OK)
async def upsert_submission(
    id: str,
    node_key: str,
    req: SubmissionUpsertRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.upsert_submission(db, user.id, id, node_key, req)

@router.post("/roadmaps/{id}/activity", status_code=status.HTTP_200_OK)
async def record_activity(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.record_activity(db, user.id, id)

@router.get("/roadmap-activity", response_model=dict[str, int], status_code=status.HTTP_200_OK)
async def get_user_activities(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user_activities(db, user.id)
