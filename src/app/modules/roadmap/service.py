import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert

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
)
from src.app.shared.Services.storage import process_image_url, delete_stored_file

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

async def get_roadmap_detail(db: AsyncSession, roadmap_id: str) -> RoadmapDetailResponse:
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
                submission=n.submission,
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
    stmt = insert(Submission).values(
        user_id=user_id,
        roadmap_id=roadmap_id,
        node_key=node_key,
        done=req.done if req.done is not None else False,
        file_name=req.file_name,
        text_answer=req.text,
        score=req.score,
        quiz_answers=req.quiz_answers,
    ).on_conflict_do_update(
        constraint="uq_user_roadmap_submission",
        set_={
            "done": req.done if req.done is not None else False,
            "file_name": req.file_name,
            "text_answer": req.text,
            "score": req.score,
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
    return SubmissionState(
        done=bool(row.done),
        fileName=row.file_name,
        text=row.text_answer,
        score=row.score,
        quizAnswers=row.quiz_answers,
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
