from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class EssayRequest(BaseModel):
    essay: str = Field(..., min_length=50)


class LLMAnalysisResponse(BaseModel):
    selected_pillars: List[str]
    confidence_score: float
    detected_traits: List[str]
    summary_reason: str
    # Jalur mana yang menghasilkan analisis ini: "llm" atau "keyword".
    # Wajib ada karena `OPENAI_API_KEY` tidak pernah ada di `.env`, jadi
    # hampir semua user sebenarnya mendapat hasil pencocokan keyword —
    # tapi dari sisi klien itu tidak bisa dibedakan dari jawaban LLM.
    method: str = "keyword"


class PillarItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class AnalyzeEssayResponse(BaseModel):
    session_id: str
    analysis: LLMAnalysisResponse
    suggested_pillars: List[PillarItem]


class QuestionItem(BaseModel):
    id: str
    pillar_id: str
    fact_id: str
    question_text: str
    question_type: str
    options: Optional[Any] = None
    sort_order: int = 0
    weight: float = 1.0


class QuestionsResponse(BaseModel):
    pillar_id: str
    questions: List[QuestionItem]


class FactItem(BaseModel):
    id: str
    name: str
    category: Optional[str] = None


class QuestionBankResponse(BaseModel):
    """Seluruh bank pertanyaan + referensi yang dibutuhkan editor dosen."""

    pillars: List[PillarItem]
    facts: List[FactItem]
    questions: List[QuestionItem]


class QuestionUpsert(BaseModel):
    """Input dari editor dosen. `id` kosong = pertanyaan baru."""

    id: Optional[str] = None
    pillar_id: str = Field(..., min_length=1)
    fact_id: str = Field(..., min_length=1)
    question_text: str = Field(..., min_length=3)
    question_type: str
    options: Optional[List[Dict[str, Any]]] = None
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class ReplaceQuestionsRequest(BaseModel):
    questions: List[QuestionUpsert] = Field(..., min_length=1)


class ReplaceQuestionsResponse(BaseModel):
    ok: bool
    count: int


class AssessmentAnswer(BaseModel):
    fact_id: str
    value: bool


class EvaluateRequest(BaseModel):
    session_id: Optional[str] = None
    pillar_id: str
    answers: List[AssessmentAnswer]


class EvaluateResponse(BaseModel):
    recommended_role: str
    recommended_role_name: str
    # Emoji ikut dikembalikan supaya frontend bisa menyimpan `Preference`
    # (roleEmoji) di localStorage tanpa harus ambil katalog role terpisah.
    recommended_role_emoji: str = ""
    match_percentage: float
    roadmap_slug: str
    all_scores: Dict[str, float]
    session_id: Optional[str] = None
