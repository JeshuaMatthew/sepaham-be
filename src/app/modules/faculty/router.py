from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import FacultyUser
from src.app.modules.faculty import service
from src.app.modules.faculty.schemas import (
    RoleResponse,
    RoleUpsertRequest,
)

router = APIRouter(prefix="/api/faculty", tags=["Faculty"])

# ===== Role Management (F#06) =====

@router.get("/roles", response_model=List[RoleResponse], status_code=status.HTTP_200_OK)
async def list_roles(
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_roles(db)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    req: RoleUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_role(db, req)


@router.put("/roles/{role_id}", response_model=RoleResponse, status_code=status.HTTP_200_OK)
async def update_role(
    role_id: str,
    req: RoleUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.update_role(db, role_id, req)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.delete_role(db, role_id)
