import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.app.modules.onboarding.entity import (
    Fact,
    Pillar,
    Question,
    Rule,
    UserOnboardingSession,
)
from src.app.modules.catalog.entity import Role, UserPreference
from src.app.modules.profile.entity import Profile
from src.app.modules.roadmap.entity import Roadmap
from src.app.modules.onboarding.schemas import (
    EssayRequest,
    AnalyzeEssayResponse,
    FactItem,
    PillarItem,
    QuestionBankResponse,
    QuestionsResponse,
    QuestionItem,
    QuestionUpsert,
    ReplaceQuestionsRequest,
    ReplaceQuestionsResponse,
    EvaluateRequest,
    EvaluateResponse,
)
from src.app.modules.onboarding.services.llm import analyze_essay_with_llm
from src.app.modules.onboarding.services.inference import forward_chaining_match


async def get_all_pillars(db: AsyncSession) -> List[PillarItem]:
    res = await db.execute(select(Pillar).order_by(Pillar.id.asc()))
    pillars = res.scalars().all()
    return [
        PillarItem(id=p.id, name=p.name, description=p.description)
        for p in pillars
    ]


async def analyze_essay(
    db: AsyncSession, req: EssayRequest, user_id: Optional[uuid.UUID] = None
) -> AnalyzeEssayResponse:
    analysis = analyze_essay_with_llm(req.essay)

    res_pillars = await db.execute(
        select(Pillar).where(Pillar.id.in_(analysis.selected_pillars))
    )
    db_pillars = res_pillars.scalars().all()
    suggested = [
        PillarItem(id=p.id, name=p.name, description=p.description)
        for p in db_pillars
    ]

    session_id = uuid.uuid4()
    session = UserOnboardingSession(
        id=session_id,
        user_id=user_id,
        essay_text=req.essay,
        selected_pillars=analysis.selected_pillars,
    )
    db.add(session)
    await db.commit()

    return AnalyzeEssayResponse(
        session_id=str(session_id),
        analysis=analysis,
        suggested_pillars=suggested,
    )


async def get_questions_by_pillar(db: AsyncSession, pillar_id: str) -> QuestionsResponse:
    res = await db.execute(
        select(Question)
        .where(Question.pillar_id == pillar_id)
        .order_by(Question.sort_order.asc(), Question.question_text.asc())
    )
    questions = res.scalars().all()
    return QuestionsResponse(
        pillar_id=pillar_id,
        questions=[_to_item(q) for q in questions],
    )


def _to_item(q: Question) -> QuestionItem:
    return QuestionItem(
        id=str(q.id),
        pillar_id=q.pillar_id or "",
        fact_id=q.fact_id or "",
        question_text=q.question_text,
        question_type=q.question_type,
        options=q.options,
        sort_order=q.sort_order or 0,
    )


async def list_question_bank(db: AsyncSession) -> QuestionBankResponse:
    """Bank pertanyaan lengkap untuk editor dosen (butuh role faculty)."""
    pillars_res = await db.execute(select(Pillar).order_by(Pillar.id.asc()))
    facts_res = await db.execute(select(Fact).order_by(Fact.category.asc(), Fact.id.asc()))
    questions_res = await db.execute(
        select(Question).order_by(
            Question.pillar_id.asc(), Question.sort_order.asc(), Question.question_text.asc()
        )
    )
    return QuestionBankResponse(
        pillars=[PillarItem(id=p.id, name=p.name, description=p.description)
                 for p in pillars_res.scalars().all()],
        facts=[FactItem(id=f.id, name=f.name, category=f.category)
               for f in facts_res.scalars().all()],
        questions=[_to_item(q) for q in questions_res.scalars().all()],
    )


_VALID_TYPES = ("binary", "scale", "choice")


async def replace_question_bank(
    db: AsyncSession, req: ReplaceQuestionsRequest
) -> ReplaceQuestionsResponse:
    """Ganti seluruh bank pertanyaan dengan isi dari editor dosen.

    Validasi ketat: pertanyaan yang tidak lengkap akan membuat mahasiswa
    terjebak di langkah itu (opsi `choice` kosong = kartu tanpa jawaban yang
    bisa dipilih), jadi data buruk ditolak di sini, bukan diteruskan.
    """
    pillar_ids = set(
        (await db.execute(select(Pillar.id))).scalars().all()
    )
    fact_ids = set((await db.execute(select(Fact.id))).scalars().all())

    seen_ids: set[str] = set()
    prepared: list[tuple[object, int, QuestionUpsert, object]] = []
    per_pillar: dict[str, int] = {}
    for idx, item in enumerate(req.questions):
        if item.question_type not in _VALID_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Pertanyaan #{idx + 1}: question_type "
                    f"'{item.question_type}' tidak dikenal "
                    f"(pilihan: {', '.join(_VALID_TYPES)})."
                ),
            )
        if item.pillar_id not in pillar_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Pertanyaan #{idx + 1}: pillar '{item.pillar_id}' tidak ada.",
            )
        if item.fact_id not in fact_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Pertanyaan #{idx + 1}: fact '{item.fact_id}' tidak ada.",
            )

        options = None
        if item.question_type == "choice":
            options = item.options or []
            if len(options) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"Pertanyaan #{idx + 1}: tipe 'choice' butuh minimal 2 opsi "
                        f"(sekarang {len(options)}). Tanpa opsi, mahasiswa tidak "
                        f"bisa menjawab sama sekali."
                    ),
                )
            option_facts: set[str] = set()
            for opt_idx, opt in enumerate(options):
                label = str(opt.get("label") or "").strip()
                fact_id = str(opt.get("fact_id") or "").strip()
                if not label:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Pertanyaan #{idx + 1}: opsi #{opt_idx + 1} belum diisi labelnya.",
                    )
                if fact_id not in fact_ids:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Pertanyaan #{idx + 1}: opsi #{opt_idx + 1} memakai fact "
                               f"'{fact_id}' yang tidak ada.",
                    )
                if fact_id in option_facts:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Pertanyaan #{idx + 1}: fact '{fact_id}' dipakai di lebih dari "
                            f"satu opsi, jadi salah satu opsi tidak pernah contribute "
                            f"apa pun ke hasil evaluasi."
                        ),
                    )
                option_facts.add(fact_id)
                options[opt_idx] = {"label": label, "fact_id": fact_id}

        qid: object | None = None
        if item.id:
            try:
                qid = uuid.UUID(item.id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Pertanyaan #{idx + 1}: id '{item.id}' bukan UUID yang valid.",
                )
            if str(qid) in seen_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Pertanyaan #{idx + 1}: id '{item.id}' muncul dua kali.",
                )
            seen_ids.add(str(qid))

        # Urutan di dalam payload yang otoritatif: indeks berjalan per pillar.
        # Ini yang membuat dosen's "naik / turun" benar-benar mengubah urutan
        # yang dilihat mahasiswa.
        order = per_pillar.get(item.pillar_id, 0)
        per_pillar[item.pillar_id] = order + 1

        prepared.append((qid, order, item, options))

    await db.execute(delete(Question))
    for qid, sort_order, item, options in prepared:
        db.add(
            Question(
                id=qid or uuid.uuid4(),
                pillar_id=item.pillar_id,
                fact_id=item.fact_id,
                question_text=item.question_text.strip(),
                question_type=item.question_type,
                options=options,
                sort_order=sort_order,
                weight=item.weight,
            )
        )
    await db.commit()
    return ReplaceQuestionsResponse(ok=True, count=len(prepared))


async def evaluate_assessment(
    db: AsyncSession, req: EvaluateRequest, user_id: Optional[uuid.UUID] = None
) -> EvaluateResponse:
    user_facts = {a.fact_id for a in req.answers if a.value}

    # Kumpulkan bobot per fact dari tabel questions
    fact_weights: Dict[str, float] = {}
    if user_facts:
        fact_rows = (
            await db.execute(
                select(Question.fact_id, Question.weight).where(
                    Question.fact_id.in_(user_facts)
                )
            )
        ).all()
        fact_weights = {fid: w for fid, w in fact_rows}

    rules_res = await db.execute(select(Rule))
    rules_list = rules_res.scalars().all()
    rules_data = [
        {"role_id": r.role_id, "conditions": r.conditions or {}}
        for r in rules_list
        if r.role_id
    ]

    match = forward_chaining_match(
        user_facts=user_facts,
        rules_from_db=rules_data,
        fallback_role="backend_dev",
        fact_weights=fact_weights,
    )

    rec_role_id = match["recommended_role"]

    role_res = await db.execute(select(Role).where(Role.id == rec_role_id))
    role_obj = role_res.scalar_one_or_none()

    role_name = role_obj.title if role_obj else rec_role_id.replace("_", " ").title()
    role_emoji = role_obj.emoji if role_obj else "💻"

    rm_res = await db.execute(select(Roadmap).where(Roadmap.role_id == rec_role_id))
    rm_obj = rm_res.scalar_one_or_none()
    roadmap_slug = rm_obj.id if rm_obj else rec_role_id

    # Update or create session
    session_uuid = None
    if req.session_id:
        try:
            session_uuid = uuid.UUID(req.session_id)
            sess_res = await db.execute(
                select(UserOnboardingSession).where(UserOnboardingSession.id == session_uuid)
            )
            sess = sess_res.scalar_one_or_none()
            if sess:
                sess.collected_facts = list(user_facts)
                sess.recommended_role_id = rec_role_id
                if user_id and not sess.user_id:
                    sess.user_id = user_id
        except Exception:
            pass

    # Persist preference to DB if user_id is available
    if user_id:
        stmt = insert(UserPreference).values(
            user_id=user_id,
            role_id=rec_role_id,
            role_title=role_name,
            role_emoji=role_emoji,
            role_scores=match["all_scores"],
        ).on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "role_id": rec_role_id,
                "role_title": role_name,
                "role_emoji": role_emoji,
                "role_scores": match["all_scores"],
            },
        )
        await db.execute(stmt)

        # `profiles` adalah SALINAN role yang dipakai hampir semua modul lain
        # (collab author_role, community member, faculty student list, AI
        # context). Kalau hanya `user_preferences` yang ditulis, role hasil
        # onboarding tidak pernah sampai ke sana dan dua tabel itu langsung
        # berbeda isi. Tulis keduanya di sini supaya onboarding jadi satu
        # sumber kebenaran.
        prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
        prof = prof_res.scalar_one_or_none()
        if prof is None:
            prof = Profile(user_id=user_id)
            db.add(prof)
        prof.role_title = role_name
        prof.role_emoji = role_emoji

    await db.commit()

    return EvaluateResponse(
        recommended_role=rec_role_id,
        recommended_role_name=role_name,
        recommended_role_emoji=role_emoji,
        match_percentage=match["match_percentage"],
        roadmap_slug=roadmap_slug,
        all_scores=match["all_scores"],
        session_id=str(session_uuid) if session_uuid else req.session_id,
    )
