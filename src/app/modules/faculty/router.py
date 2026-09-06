import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import FacultyUser
from src.app.modules.faculty import service
from src.app.modules.faculty.schemas import (
    FacultyStudentsResponse,
    FacultyServersResponse,
    BanServerResponse,
    FacultyRequestsResponse,
    CloseCollabRequestResponse,
)

router = APIRouter(prefix="/api/faculty", tags=["Faculty"])

@router.get("/students", response_model=FacultyStudentsResponse, status_code=status.HTTP_200_OK)
async def get_students(
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_students(db)

@router.get("/servers", response_model=FacultyServersResponse, status_code=status.HTTP_200_OK)
async def get_servers(
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_servers(db)

@router.post("/servers/{id}/ban", response_model=BanServerResponse, status_code=status.HTTP_200_OK)
async def ban_server(
    id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.ban_server(db, faculty.id, id)

@router.get("/requests", response_model=FacultyRequestsResponse, status_code=status.HTTP_200_OK)
async def get_requests(
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_requests(db)

@router.post("/requests/{id}/close", response_model=CloseCollabRequestResponse, status_code=status.HTTP_200_OK)
async def close_request(
    id: uuid.UUID,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.close_request(db, id)

