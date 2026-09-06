from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.auth.schemas import RegisterRequest, LoginRequest, AuthResponse, UserDetail
from src.app.modules.auth import service

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await service.register(db, req)

@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.login(db, req)

@router.get("/me", response_model=UserDetail, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_me(db, user.id)
