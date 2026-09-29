from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import get_db
from src.app.shared.dependencies import FacultyUser, OptionalCurrentUser
from src.app.modules.onboarding.schemas import (
    EssayRequest,
    AnalyzeEssayResponse,
    PillarItem,
    QuestionsResponse,
    QuestionBankResponse,
    ReplaceQuestionsRequest,
    ReplaceQuestionsResponse,
    EvaluateRequest,
    EvaluateResponse,
)
from src.app.modules.onboarding.services import (
    get_all_pillars,
    analyze_essay,
    get_questions_by_pillar,
    list_question_bank,
    replace_question_bank,
    evaluate_assessment,
)

router = APIRouter(tags=["Onboarding"])


@router.get("/pillars", response_model=List[PillarItem], status_code=status.HTTP_200_OK)
async def list_pillars(db: AsyncSession = Depends(get_db)):
    return await get_all_pillars(db)


@router.post("/analyze-essay", response_model=AnalyzeEssayResponse, status_code=status.HTTP_200_OK)
async def handle_analyze_essay(
    req: EssayRequest,
    user: OptionalCurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id if user else None
    return await analyze_essay(db, req, user_id=user_id)


@router.get("/questions", response_model=QuestionsResponse, status_code=status.HTTP_200_OK)
async def list_questions(
    pillar: str = Query(..., description="Pillar ID"),
    db: AsyncSession = Depends(get_db),
):
    return await get_questions_by_pillar(db, pillar)


@router.get(
    "/questions/bank",
    response_model=QuestionBankResponse,
    status_code=status.HTTP_200_OK,
)
async def list_question_bank_route(
    _faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Seluruh bank pertanyaan — hanya untuk editor soal dosen."""
    return await list_question_bank(db)


@router.put(
    "/questions",
    response_model=ReplaceQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def replace_questions_route(
    req: ReplaceQuestionsRequest,
    _faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Ganti seluruh bank pertanyaan. Hanya untuk editor soal dosen."""
    return await replace_question_bank(db, req)


@router.post("/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK)
async def handle_evaluate(
    req: EvaluateRequest,
    user: OptionalCurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id if user else None
    return await evaluate_assessment(db, req, user_id=user_id)
