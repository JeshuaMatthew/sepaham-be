import uuid
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.collab import service
from src.app.modules.collab.schemas import (
    CollabRequestItem,
    CollabRequestsResponse,
    CreateCollabRequest,
    ApplicantItem,
    MyTeamsResponse,
    ApplyCollabRequest,
    UpdateApplicantStatusRequest,
)

router = APIRouter(prefix="/api/collab", tags=["Collab"])

@router.get("/requests", response_model=CollabRequestsResponse, status_code=status.HTTP_200_OK)
async def get_requests(db: AsyncSession = Depends(get_db)):
    return await service.get_requests(db)

@router.post("/requests", response_model=CollabRequestItem, status_code=status.HTTP_201_CREATED)
async def create_request(
    req: CreateCollabRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_request(db, user.id, req)

@router.delete("/requests/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await service.delete_request(db, user.id, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/my-teams", response_model=MyTeamsResponse, status_code=status.HTTP_200_OK)
async def get_my_teams(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_my_teams(db, user.id)

@router.post("/requests/{id}/apply", response_model=ApplicantItem, status_code=status.HTTP_201_CREATED)
async def apply_request(
    id: uuid.UUID,
    req: ApplyCollabRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.apply_request(db, user.id, id, req.message)

@router.patch("/requests/{id}/applicants/{applicant_id}", response_model=ApplicantItem, status_code=status.HTTP_200_OK)
async def update_applicant_status(
    id: uuid.UUID,
    applicant_id: uuid.UUID,
    req: UpdateApplicantStatusRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update_applicant_status(db, user.id, id, applicant_id, req.status)
