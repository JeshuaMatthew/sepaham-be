from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser
from src.app.modules.ai import service
from src.app.modules.ai.schemas import (
    AiAssistRequest,
    AiAssistResponse,
    AiGenerateRequest,
    AiGenerateResponse,
)

router = APIRouter(prefix="/api/ai", tags=["AI"])


# Kedua endpoint ini memanggil LLM berbayar. Sebelumnya `OptionalCurrentUser`
# yang dipakai, jadi siapa pun tanpa token bisa menghabiskan kuota API, dan
# konteks yang dikembalikan adalah data karangan karena tidak ada user asli.


@router.post("/assist", response_model=AiAssistResponse, status_code=status.HTTP_200_OK)
async def ai_assist(
    req: AiAssistRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.assist(db, req, user_id=user.id)


@router.post("/generate", response_model=AiGenerateResponse, status_code=status.HTTP_200_OK)
async def ai_generate(
    req: AiGenerateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.generate(db, req, user_id=user.id)
