from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text as sa_text
from sqlalchemy.orm import selectinload

from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.community.entity import Server, Channel, ServerMember
from src.app.modules.collab.entity import CollabRequest, CollabRequestImage, CollabApplicant
from src.app.modules.collab.schemas import (
    AuthorObj,
    CollabRequestItem,
    CollabRequestsResponse,
    CreateCollabRequest,
    ApplicantItem,
    MyTeamItem,
    MyTeamsResponse,
)
from src.app.shared.Services.storage import process_image_url, delete_stored_file

def _to_request_item(c: CollabRequest, server_name: str = None, interested_count: int = 0) -> CollabRequestItem:
    now = datetime.now(timezone.utc)
    created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
    diff_minutes = max(0, int((now - created).total_seconds() // 60))
    status_str = c.status.value if hasattr(c.status, "value") else str(c.status)

    images = [img.url for img in sorted(c.images, key=lambda x: x.sort_order)] if c.images else []

    return CollabRequestItem(
        id=str(c.id),
        title=c.title,
        description=c.description or "",
        neededRoles=c.needed_roles or [],
        techStack=c.tech_stack or [],
        tags=c.tags or [],
        repoUrl=c.repo_url,
        images=images,
        communityId=c.community_id,
        communityName=server_name or (c.server.name if c.server else None),
        author=AuthorObj(
            name=c.author_name,
            avatar=c.author_avatar or "",
            role=c.author_role or "",
        ),
        membersCurrent=c.members_current,
        membersNeeded=c.members_needed,
        interested=interested_count,
        status=status_str,
        postedMinutesAgo=diff_minutes,
    )

async def get_requests(db: AsyncSession, include_closed: bool = False) -> CollabRequestsResponse:
    stmt = (
        select(CollabRequest)
        .options(selectinload(CollabRequest.images), selectinload(CollabRequest.server))
        .order_by(CollabRequest.created_at.desc())
    )
    if not include_closed:
        stmt = stmt.where(CollabRequest.closed == False)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    items = []
    for c in requests:
        cnt_res = await db.scalar(
            select(func.count(CollabApplicant.id)).where(CollabApplicant.request_id == c.id)
        )
        items.append(_to_request_item(c, interested_count=cnt_res or 0))

    return CollabRequestsResponse(requests=items)

async def create_request(
    db: AsyncSession, user_id: uuid.UUID, req: CreateCollabRequest
) -> CollabRequestItem:
    # 1. Fetch user & profile info
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()

    author_name = user.name if user else "User"
    author_avatar = profile.avatar_url if profile else ""
    author_role = profile.role_title if profile else ""

    # 2. Handle community
    community_id = req.community_id
    server_name = None
    if community_id:
        srv = await db.get(Server, community_id)
        if srv:
            server_name = srv.name
    else:
        # Create new team server
        s_id = f"tim-{uuid.uuid4().hex[:8]}"
        s_name = req.new_community_name or f"Tim {req.title[:20]}"
        initial = s_name[:2].upper()
        server = Server(
            id=s_id,
            name=s_name,
            initial=initial,
            color="#e5e5e5",
            owner_id=user_id,
            is_team_community=True,
        )
        db.add(server)
        await db.flush()

        # Add 2 default channels: general & progress
        db.add(Channel(id=f"{s_id}-general", server_id=s_id, name="general", topic="", sort_order=1))
        db.add(Channel(id=f"{s_id}-progress", server_id=s_id, name="progress", topic="Update progres & to-do proyek", sort_order=2))
        db.add(ServerMember(server_id=s_id, user_id=user_id))
        community_id = s_id
        server_name = s_name

    # 3. Create CollabRequest
    collab = CollabRequest(
        author_id=user_id,
        author_name=author_name,
        author_avatar=author_avatar or "",
        author_role=author_role or "",
        title=req.title,
        description=req.description or "",
        needed_roles=req.needed_roles or [],
        tech_stack=req.tech_stack or [],
        tags=req.tags or [],
        repo_url=req.repo_url,
        community_id=community_id,
        members_current=1,
        members_needed=max(2, req.members_needed),
        status="open",
    )
    db.add(collab)
    await db.flush()

    # 4. Process Images
    if req.images:
        for idx, img_data in enumerate(req.images):
            processed_url = await process_image_url(img_data)
            if processed_url:
                db.add(CollabRequestImage(request_id=collab.id, url=processed_url, sort_order=idx))

    await db.commit()
    await db.refresh(collab)

    # Re-fetch with images
    stmt = select(CollabRequest).options(selectinload(CollabRequest.images)).where(CollabRequest.id == collab.id)
    c_res = await db.execute(stmt)
    collab = c_res.scalar_one()

    return _to_request_item(collab, server_name=server_name, interested_count=0)

async def delete_request(db: AsyncSession, user_id: uuid.UUID, req_id: uuid.UUID) -> None:
    c = await db.get(CollabRequest, req_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request tidak ditemukan")
    if c.author_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan pembuat request")

    # Get images to delete from disk
    imgs_res = await db.execute(select(CollabRequestImage.url).where(CollabRequestImage.request_id == req_id))
    img_urls = imgs_res.scalars().all()

    await db.delete(c)
    await db.commit()

    for u in img_urls:
        delete_stored_file(u)

async def get_my_teams(db: AsyncSession, user_id: uuid.UUID) -> MyTeamsResponse:
    stmt = (
        select(CollabRequest)
        .options(selectinload(CollabRequest.images), selectinload(CollabRequest.server))
        .where(CollabRequest.author_id == user_id)
        .order_by(CollabRequest.created_at.desc())
    )
    result = await db.execute(stmt)
    my_requests = result.scalars().all()

    now = datetime.now(timezone.utc)
    teams = []
    for c in my_requests:
        apps_res = await db.execute(
            select(CollabApplicant)
            .where(CollabApplicant.request_id == c.id)
            .order_by(CollabApplicant.created_at.asc())
        )
        applicants = apps_res.scalars().all()

        app_items = []
        for a in applicants:
            c_time = a.created_at if a.created_at.tzinfo else a.created_at.replace(tzinfo=timezone.utc)
            mins = max(0, int((now - c_time).total_seconds() // 60))
            st_val = a.status.value if hasattr(a.status, "value") else str(a.status)
            app_items.append(
                ApplicantItem(
                    id=str(a.id),
                    name=a.name,
                    avatar=a.avatar or "",
                    role=a.role or "",
                    message=a.message,
                    status=st_val,
                    appliedMinutesAgo=mins,
                )
            )

        teams.append(
            MyTeamItem(
                request=_to_request_item(c, interested_count=len(applicants)),
                applicants=app_items,
                communityServerId=c.community_id,
            )
        )

    return MyTeamsResponse(teams=teams)

async def apply_request(
    db: AsyncSession, user_id: uuid.UUID, req_id: uuid.UUID, message: str = None
) -> ApplicantItem:
    c = await db.get(CollabRequest, req_id)
    if not c or c.closed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request tidak ditemukan atau sudah ditutup")
    if c.author_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tidak dapat melamar ke request sendiri")

    # Check duplicate apply
    dup_res = await db.execute(
        select(CollabApplicant).where(CollabApplicant.request_id == req_id, CollabApplicant.user_id == user_id)
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sudah pernah melamar")

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()

    applicant = CollabApplicant(
        request_id=req_id,
        user_id=user_id,
        name=user.name if user else "User",
        avatar=profile.avatar_url if profile else "",
        role=profile.role_title if profile else "",
        message=message,
        status="pending",
    )
    db.add(applicant)
    await db.commit()
    await db.refresh(applicant)

    return ApplicantItem(
        id=str(applicant.id),
        name=applicant.name,
        avatar=applicant.avatar or "",
        role=applicant.role or "",
        message=applicant.message,
        status="pending",
        appliedMinutesAgo=0,
    )

async def update_applicant_status(
    db: AsyncSession, user_id: uuid.UUID, req_id: uuid.UUID, applicant_id: uuid.UUID, status_val: str
) -> ApplicantItem:
    c = await db.get(CollabRequest, req_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request tidak ditemukan")
    if c.author_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan pembuat request")

    applicant = await db.get(CollabApplicant, applicant_id)
    if not applicant or applicant.request_id != req_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pelamar tidak ditemukan")

    old_status = applicant.status.value if hasattr(applicant.status, "value") else str(applicant.status)
    applicant.status = status_val

    # If accepted and was not accepted before
    if status_val == "accepted" and old_status != "accepted":
        if c.community_id and applicant.user_id:
            # Add to server members
            mem_res = await db.execute(
                select(ServerMember).where(
                    ServerMember.server_id == c.community_id, ServerMember.user_id == applicant.user_id
                )
            )
            if not mem_res.scalar_one_or_none():
                db.add(ServerMember(server_id=c.community_id, user_id=applicant.user_id))

        c.members_current = min(c.members_current + 1, c.members_needed)
        if c.members_current >= c.members_needed:
            c.status = "full"

    await db.commit()
    await db.refresh(applicant)

    now = datetime.now(timezone.utc)
    c_time = applicant.created_at if applicant.created_at.tzinfo else applicant.created_at.replace(tzinfo=timezone.utc)
    mins = max(0, int((now - c_time).total_seconds() // 60))

    return ApplicantItem(
        id=str(applicant.id),
        name=applicant.name,
        avatar=applicant.avatar or "",
        role=applicant.role or "",
        message=applicant.message,
        status=status_val,
        appliedMinutesAgo=mins,
    )
