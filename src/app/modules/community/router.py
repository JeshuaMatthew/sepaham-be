import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.community import service
from src.app.modules.community.schemas import (
    CommunityMineResponse,
    JoinServerResponse,
    CreateInviteResponse,
    MessageResponse,
    PostMessageRequest,
    DMItem,
    DMsResponse,
    CreateDMRequest,
)

community_router = APIRouter(prefix="/api/community", tags=["Community"])
chat_router = APIRouter(prefix="/api", tags=["Chat"])

# --- Community Endpoints ---

@community_router.get("/mine", response_model=CommunityMineResponse, status_code=status.HTTP_200_OK)
async def get_my_communities(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_my_communities(db, user.id)

@community_router.post("/servers/{id}/join", response_model=JoinServerResponse, status_code=status.HTTP_200_OK)
async def join_server(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.join_server(db, user.id, id)

@community_router.post("/servers/{id}/invites", response_model=CreateInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_invite(db, user.id, id)

@community_router.post("/invites/{token}/accept", response_model=JoinServerResponse, status_code=status.HTTP_200_OK)
async def accept_invite(
    token: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.accept_invite(db, user.id, token)

# --- Channel Chat Endpoints ---

@chat_router.get("/channels/{channel_id}/messages", response_model=list[MessageResponse], status_code=status.HTTP_200_OK)
async def get_channel_messages(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_channel_messages(db, channel_id)

@chat_router.post("/channels/{channel_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def post_channel_message(
    channel_id: str,
    req: PostMessageRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.post_channel_message(db, user.id, channel_id, req)

# --- DM Chat Endpoints ---

@chat_router.get("/dms", response_model=DMsResponse, status_code=status.HTTP_200_OK)
async def get_dms(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_dms(db, user.id)

@chat_router.post("/dms", response_model=DMItem, status_code=status.HTTP_200_OK)
async def create_dm(
    req: CreateDMRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.create_or_get_dm(db, user.id, uuid.UUID(req.user_id))

@chat_router.post("/dms/{dm_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def post_dm_message(
    dm_id: uuid.UUID,
    req: PostMessageRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.post_dm_message(db, user.id, dm_id, req)
