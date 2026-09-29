import uuid
from typing import Any, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert

from src.app.core.config import settings
from src.app.modules.roadmap.entity import (
    Roadmap,
    RoadmapNode,
    RoadmapEdge,
    Submission,
    RoadmapActivity,
)
from src.app.modules.roadmap.schemas import (
    RoadmapListItem,
    RoadmapsListResponse,
    NodeItem,
    EdgeItem,
    RoadmapDetailResponse,
    RoadmapUpsertRequest,
    SubmissionState,
    SubmissionUpsertRequest,
    UploadedFileResponse,
)
from src.app.shared.Services.storage import process_image_url, delete_stored_file

# Yang TIDAK boleh keluar dari server hanya kunci jawaban. Ambang kelulusan
# (`passingScore`) justru harus ikut terkirim: mahasiswa perlu tahu targetnya,
# dan UI harus menampilkan angka yang sama dengan yang ditegakkan server.
# Kalau `passingScore` ikut dibuang, frontend jatuh ke default-nya sendiri dan
# menampilkan ambang yang berbeda dari yang sebenarnya dipakai penilaian.
_ANSWER_KEY_FIELDS = ("correctIndex", "correct_index")


def sanitize_submission_payload(payload: Any) -> Any:
    """Salinan payload submission tanpa kunci jawaban per soal."""
    if not isinstance(payload, dict):
        return payload

    clean = {key: value for key, value in payload.items() if key not in _ANSWER_KEY_FIELDS}

    questions = clean.get("questions")
    if isinstance(questions, list):
        clean["questions"] = [
            {k: v for k, v in q.items() if k not in _ANSWER_KEY_FIELDS}
            if isinstance(q, dict)
            else q
            for q in questions
        ]

    return clean


class QuizGrade:
    """Hasil penilaian quiz yang dihitung server."""

    def __init__(self, score: int, passed: bool, detail: dict) -> None:
        self.score = score
        self.passed = passed
        self.detail = detail


def grade_quiz(quiz: dict, answers: Any) -> Optional[QuizGrade]:
    """Nilai jawaban quiz terhadap `correctIndex` di server.

    `answers` diterima dalam dua bentuk karena frontend mengirim
    `{ questionId: selectedIndex }` maupun daftar
    `[{ questionId, selected }]`:
    - dict  -> dipakai langsung
    - list  -> diratakan memakai `questionId` dan `selected`

    Mengembalikan `None` kalau `quiz` bukan bentuk quiz atau tidak punya
    kunci jawaban, supaya pemanggil tidak menebak.
    """
    questions = quiz.get("questions")
    if not isinstance(questions, list) or not questions:
        return None

    if not any(
        isinstance(q, dict) and "correctIndex" in q
        for q in questions
    ):
        return None

    if isinstance(answers, dict):
        selected_by_id = {str(k): v for k, v in answers.items()}
    elif isinstance(answers, list):
        selected_by_id = {}
        for item in answers:
            if isinstance(item, dict):
                qid = item.get("questionId", item.get("question_id"))
                if qid is not None:
                    selected_by_id[str(qid)] = item.get(
                        "selected", item.get("selectedIndex")
                    )
    else:
        selected_by_id = {}

    total = len(questions)
    correct = 0
    per_question = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        qid = str(question.get("id", ""))
        correct_index = question.get("correctIndex")
        selected = selected_by_id.get(qid)
        is_correct = selected is not None and selected == correct_index
        if is_correct:
            correct += 1
        per_question.append({"questionId": qid, "correct": is_correct})

    score = round((correct / total) * 100) if total else 0
    passing = int(quiz.get("passingScore") or 0)

    return QuizGrade(
        score=score,
        passed=score >= passing,
        detail={
            "correct": correct,
            "total": total,
            "passingScore": passing,
            "questions": per_question,
        },
    )


async def get_roadmaps(db: AsyncSession) -> RoadmapsListResponse:
    stmt = (
        select(
            Roadmap.id,
            Roadmap.role_id,
            Roadmap.title,
            Roadmap.emoji,
            Roadmap.color,
            Roadmap.description,
            Roadmap.difficulty,
            Roadmap.match_tags,
            Roadmap.author,
            func.count(RoadmapNode.id).label("total_nodes"),
        )
        .outerjoin(RoadmapNode, RoadmapNode.roadmap_id == Roadmap.id)
        .group_by(Roadmap.id)
        .order_by(Roadmap.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for r in rows:
        diff_val = r.difficulty.value if hasattr(r.difficulty, "value") else str(r.difficulty)
        items.append(
            RoadmapListItem(
                id=r.id,
                roleId=r.role_id,
                title=r.title,
                emoji=r.emoji or "",
                color=r.color or "",
                description=r.description or "",
                difficulty=diff_val,
                matchTags=r.match_tags or [],
                author=r.author or "",
                totalNodes=r.total_nodes or 0,
            )
        )
    return RoadmapsListResponse(roadmaps=items)

async def get_roadmap_detail(
    db: AsyncSession, roadmap_id: str, include_answer_key: bool = False
) -> RoadmapDetailResponse:
    res = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    rm = res.scalar_one_or_none()
    if not rm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap tidak ditemukan")

    # Get nodes
    nodes_res = await db.execute(
        select(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap_id).order_by(RoadmapNode.sort_order.asc())
    )
    nodes = nodes_res.scalars().all()

    # Get edges
    edges_res = await db.execute(
        select(RoadmapEdge).where(RoadmapEdge.roadmap_id == roadmap_id)
    )
    edges = edges_res.scalars().all()

    return RoadmapDetailResponse(
        id=rm.id,
        roleId=rm.role_id,
        title=rm.title,
        emoji=rm.emoji or "",
        author=rm.author or "",
        style=rm.style or {},
        nodes=[
            NodeItem(
                id=n.node_key,
                title=n.title,
                emoji=n.emoji or "",
                x=n.x,
                y=n.y,
                group=n.group_name,
                image=n.image,
                titleInside=n.title_inside,
                alwaysUnlocked=n.always_unlocked,
                optional=n.optional,
                article=n.article,
                # Kunci jawaban dibuang sebelum dikirim ke mahasiswa. Hanya
                # endpoint faculty yang boleh meminta payload apa adanya.
                submission=(
                    n.submission
                    if include_answer_key
                    else sanitize_submission_payload(n.submission)
                ),
                resources=n.resources,
                missions=n.missions,
            )
            for n in nodes
        ],
        edges=[
            EdgeItem(
                id=e.edge_key,
                source=e.source_key,
                target=e.target_key,
                dashed=e.dashed,
                optional=e.optional,
                animated=e.animated,
            )
            for e in edges
        ],
    )

async def upsert_roadmap(
    db: AsyncSession, roadmap_id: str, req: RoadmapUpsertRequest, user_id: uuid.UUID
) -> dict:
    # 1. Upsert roadmap metadata
    existing_res = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    rm = existing_res.scalar_one_or_none()

    role_id_to_save = req.role_id
    if role_id_to_save:
        from src.app.modules.catalog.entity import Role
        role_exists = await db.scalar(select(Role.id).where(Role.id == role_id_to_save))
        if not role_exists:
            role_id_to_save = None

    if not rm:
        rm = Roadmap(
            id=roadmap_id,
            role_id=role_id_to_save,
            title=req.title or roadmap_id,
            emoji=req.emoji or "",
            color=req.color or "",
            description=req.description or "",
            difficulty=req.difficulty or "Beginner",
            match_tags=req.match_tags or [],
            author=req.author or "",
            style=req.style or {},
            created_by=user_id,
        )
        db.add(rm)
    else:
        if req.role_id is not None:
            rm.role_id = role_id_to_save
        if req.title is not None:
            rm.title = req.title
        if req.emoji is not None:
            rm.emoji = req.emoji
        if req.color is not None:
            rm.color = req.color
        if req.description is not None:
            rm.description = req.description
        if req.difficulty is not None:
            rm.difficulty = req.difficulty
        if req.match_tags is not None:
            rm.match_tags = req.match_tags
        if req.author is not None:
            rm.author = req.author
        if req.style is not None:
            rm.style = req.style

    # 2. Get old node images for cleanup
    old_nodes_res = await db.execute(
        select(RoadmapNode.image).where(RoadmapNode.roadmap_id == roadmap_id, RoadmapNode.image.isnot(None))
    )
    old_images = set(img for img in old_nodes_res.scalars().all() if img)

    # 3. Replace nodes if provided
    new_images = set()
    if req.nodes is not None:
        await db.execute(delete(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap_id))
        for idx, node in enumerate(req.nodes):
            processed_img = await process_image_url(node.image) if node.image else None
            if processed_img:
                new_images.add(processed_img)
            db.add(
                RoadmapNode(
                    roadmap_id=roadmap_id,
                    node_key=node.id,
                    title=node.title,
                    emoji=node.emoji or "",
                    x=node.x,
                    y=node.y,
                    group_name=node.group,
                    image=processed_img,
                    title_inside=node.title_inside,
                    always_unlocked=node.always_unlocked,
                    optional=node.optional,
                    article=node.article,
                    submission=node.submission,
                    resources=node.resources,
                    missions=node.missions,
                    sort_order=idx,
                )
            )

    # 4. Replace edges if provided
    if req.edges is not None:
        await db.execute(delete(RoadmapEdge).where(RoadmapEdge.roadmap_id == roadmap_id))
        for edge in req.edges:
            db.add(
                RoadmapEdge(
                    roadmap_id=roadmap_id,
                    edge_key=edge.id,
                    source_key=edge.source,
                    target_key=edge.target,
                    dashed=edge.dashed,
                    optional=edge.optional,
                    animated=edge.animated,
                )
            )

    await db.commit()

    # Clean up unreferenced old images
    unused_images = old_images - new_images
    for img_url in unused_images:
        delete_stored_file(img_url)

    return {"id": roadmap_id, "ok": True}

async def create_roadmap(
    db: AsyncSession, req: RoadmapUpsertRequest, user_id: uuid.UUID
) -> dict:
    """Buat roadmap baru dengan id dari server.

    Sebelumnya frontend membuat id `custom-xxxxxxxx` di browser lalu `PUT` ke
    id yang belum ada di server (error ditelan), sehingga roadmap hanya hidup
    di localStorage satu browser. Sekarang id dibuat di sini dari judul plus
    akhiran acak supaya unik, dan roadmap langsung tersimpan di database.
    """
    import re as _re

    slug = _re.sub(r"[^a-z0-9]+", "-", (req.title or "roadmap").lower()).strip("-") or "roadmap"
    roadmap_id = f"{slug}-{uuid.uuid4().hex[:6]}"

    existing = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    while existing.scalar_one_or_none() is not None:
        roadmap_id = f"{slug}-{uuid.uuid4().hex[:6]}"
        existing = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))

    return await upsert_roadmap(db, roadmap_id, req, user_id)

async def delete_roadmap(db: AsyncSession, roadmap_id: str) -> dict:
    """Hapus roadmap beserta node/edge/submission-nya.

    Relasi `nodes`/`edges` memakai cascade delete-orphan, dan `submissions` /
    `roadmap_activity` memakai FK `ON DELETE CASCADE`, jadi cukup hapus baris
    roadmap-nya. Sebelumnya tidak ada endpoint ini sama sekali: tombol hapus di
    UI hanya membuang item dari array lokal, dan roadmap muncul lagi di
    browser lain.
    """
    res = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))
    rm = res.scalar_one_or_none()
    if rm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap tidak ditemukan",
        )
    await db.delete(rm)
    await db.commit()
    return {"id": roadmap_id, "ok": True}

async def get_submissions(
    db: AsyncSession, user_id: uuid.UUID, roadmap_id: str
) -> dict[str, SubmissionState]:
    res = await db.execute(
        select(Submission).where(Submission.user_id == user_id, Submission.roadmap_id == roadmap_id)
    )
    subs = res.scalars().all()
    return {
        s.node_key: SubmissionState(
            done=bool(s.done),
            fileName=s.file_name,
            text=s.text_answer,
            score=s.score,
            quizAnswers=s.quiz_answers,
        )
        for s in subs
    }

async def upsert_submission(
    db: AsyncSession,
    user_id: uuid.UUID,
    roadmap_id: str,
    node_key: str,
    req: SubmissionUpsertRequest,
) -> SubmissionState:
    """Simpan submission dan, untuk node quiz, nilai di server.

    `done` dan `score` tidak lagi datang dari client. Yang client kirim hanya
    bukti: jawaban quiz, teks, atau nama berkas. Server yang memutuskan
    apakah node selesai.
    """
    node_res = await db.execute(
        select(RoadmapNode).where(
            RoadmapNode.roadmap_id == roadmap_id,
            RoadmapNode.node_key == node_key,
        )
    )
    node = node_res.scalar_one_or_none()
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node roadmap tidak ditemukan",
        )

    payload = node.submission if isinstance(node.submission, dict) else {}
    submission_type = payload.get("type")

    score: Optional[int] = None
    score_detail: Optional[dict] = None
    done = False

    if submission_type == "quiz":
        grade = grade_quiz(payload, req.quiz_answers)
        if grade is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Node ini bukan quiz yang bisa dinilai, atau kunci jawabannya belum diatur.",
            )
        score = grade.score
        score_detail = grade.detail
        done = grade.passed
    elif submission_type == "text":
        done = bool((req.text or "").strip())
    elif submission_type == "file":
        # `file_name` hanya diisi kalau benar-benar ada berkas yang diunggah
        # lewat endpoint upload. Node tidak bisa diselesaikan dengan mengetik
        # nama berkas.
        done = bool(req.file_name)
    elif submission_type == "checkmark":
        # Deklarasi diri, bukan verifikasi. Disimpan supaya progres tidak
        # hilang, dan ditandai supaya UI bisa jujur soal statusnya.
        done = True
        score_detail = {"selfDeclared": True}
    else:
        # Tipe submission tidak dikenal: jangan tandai selesai, tapi jangan
        # juga tolak — biarkan data tersimpan untuk diperiksa.
        done = False

    stmt = insert(Submission).values(
        user_id=user_id,
        roadmap_id=roadmap_id,
        node_key=node_key,
        done=done,
        file_name=req.file_name,
        text_answer=req.text,
        score=score,
        quiz_answers=req.quiz_answers,
    ).on_conflict_do_update(
        constraint="uq_user_roadmap_submission",
        set_={
            "done": done,
            "file_name": req.file_name,
            "text_answer": req.text,
            "score": score,
            "quiz_answers": req.quiz_answers,
        },
    ).returning(
        Submission.node_key,
        Submission.done,
        Submission.file_name,
        Submission.text_answer,
        Submission.score,
        Submission.quiz_answers,
    )
    res = await db.execute(stmt)
    await db.commit()
    row = res.one()

    # Badge dihitung dari aksi nyata (di sini: submission selesai). Kegagalan
    # pemberian badge tidak boleh menggagalkan submission.
    try:
        from src.app.modules.badges.service import award_badges_for_user

        await award_badges_for_user(db, user_id)
    except Exception:
        pass

    return SubmissionState(
        done=bool(row.done),
        fileName=row.file_name,
        text=row.text_answer,
        score=row.score,
        quizAnswers=row.quiz_answers,
        scoreDetail=score_detail,
    )

async def upload_submission_file(
    db: AsyncSession,
    user_id: uuid.UUID,
    roadmap_id: str,
    node_key: str,
    file: UploadFile,
) -> UploadedFileResponse:
    """Unggah bukti berkas dan tandai node selesai.

    Berkas benar-benar ditulis ke `uploads/`, jadi nama yang sampai ke tabel
    `submissions.file_name` menunjuk berkas yang ada. Sebelumnya UI hanya
    mengirim `File.name` tanpa unggah apa pun.
    """
    node_res = await db.execute(
        select(RoadmapNode).where(
            RoadmapNode.roadmap_id == roadmap_id,
            RoadmapNode.node_key == node_key,
        )
    )
    node = node_res.scalar_one_or_none()
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node roadmap tidak ditemukan",
        )

    payload = node.submission if isinstance(node.submission, dict) else {}
    if payload.get("type") != "file":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Node ini tidak meminta berkas sebagai bukti.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Berkas kosong.",
        )

    file_name = await save_uploaded_file(file)
    await db.commit()

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return UploadedFileResponse(
        fileName=file_name,
        url=f"{base}/uploads/{file_name}",
        size=len(content),
    )


async def record_activity(db: AsyncSession, user_id: uuid.UUID, roadmap_id: str) -> dict:
    stmt = insert(RoadmapActivity).values(
        user_id=user_id,
        roadmap_id=roadmap_id,
    ).on_conflict_do_update(
        index_elements=["user_id", "roadmap_id"],
        set_={"last_active_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}

async def get_user_activities(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    stmt = select(
        RoadmapActivity.roadmap_id,
        RoadmapActivity.last_active_at,
    ).where(RoadmapActivity.user_id == user_id)
    res = await db.execute(stmt)
    rows = res.all()
    return {r.roadmap_id: int(r.last_active_at.timestamp() * 1000) for r in rows if r.last_active_at}
