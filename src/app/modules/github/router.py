from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.github import service
from src.app.modules.github.schemas import GithubCardResponse, GithubConnectRequest

router = APIRouter(prefix="/api/github", tags=["GitHub"])

@router.get("", response_model=GithubCardResponse, status_code=status.HTTP_200_OK)
async def get_github_card(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await service.get_github_card(db, user.id)

@router.post("/connect", response_model=GithubCardResponse, status_code=status.HTTP_200_OK)
async def connect_github(
    req: GithubConnectRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.connect_github(db, user.id, req)

@router.delete("/connect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await service.disconnect_github(db, user.id)

