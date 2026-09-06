from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.badges.entity import Badge
from src.app.modules.userBadge.entity import UserBadge
from src.app.modules.profile.schemas import ProfileResponse, ProfileUpdateRequest, CVResponse, BadgeItem
from src.app.shared.Services.storage import process_image_url, save_uploaded_file, delete_stored_file

async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> ProfileResponse:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")

    res_p = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res_p.scalar_one_or_none()
    if not profile:
        # Create default profile if missing
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return ProfileResponse(
        avatar_url=profile.avatar_url or "",
        name=user.name,
        username=profile.username or "",
        university=profile.university or "",
        batch=profile.batch,
        role=profile.role_title or "",
        role_emoji=profile.role_emoji or "",
        bio=profile.bio or "",
        location=profile.location or "",
        github_connected=bool(profile.github_connected),
        github_username=profile.github_username,
        cv_file_name=profile.cv_file_name,
        cv_uploaded_at=profile.cv_uploaded_at,
    )

async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, req: ProfileUpdateRequest
) -> ProfileResponse:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")

    res_p = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res_p.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)

    # Check username uniqueness if changed
    if req.username is not None and req.username != profile.username:
        existing = await db.execute(
            select(Profile).where(Profile.username == req.username, Profile.user_id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username sudah digunakan",
            )
        profile.username = req.username

    # Update name in User entity
    if req.name is not None:
        user.name = req.name.strip()

    # Update avatar
    if req.avatar_url is not None:
        old_avatar = profile.avatar_url
        new_avatar = await process_image_url(req.avatar_url)
        profile.avatar_url = new_avatar or ""
        # If changed and old was local, delete old file
        if old_avatar and old_avatar != profile.avatar_url and "/uploads/" in old_avatar:
            delete_stored_file(old_avatar)

    # Update profile fields
    if req.university is not None:
        profile.university = req.university
    if req.batch is not None:
        profile.batch = req.batch
    if req.role is not None:
        profile.role_title = req.role
    if req.role_emoji is not None:
        profile.role_emoji = req.role_emoji
    if req.bio is not None:
        profile.bio = req.bio
    if req.location is not None:
        profile.location = req.location

    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)

    return ProfileResponse(
        avatar_url=profile.avatar_url or "",
        name=user.name,
        username=profile.username or "",
        university=profile.university or "",
        batch=profile.batch,
        role=profile.role_title or "",
        role_emoji=profile.role_emoji or "",
        bio=profile.bio or "",
        location=profile.location or "",
        github_connected=bool(profile.github_connected),
        github_username=profile.github_username,
        cv_file_name=profile.cv_file_name,
        cv_uploaded_at=profile.cv_uploaded_at,
    )

async def upload_cv(db: AsyncSession, user_id: uuid.UUID, file: UploadFile) -> CVResponse:
    res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)

    # Delete old CV if exists
    if profile.cv_file_name:
        delete_stored_file(profile.cv_file_name)

    saved_file_name = await save_uploaded_file(file)
    now = datetime.now(timezone.utc)
    profile.cv_file_name = saved_file_name
    profile.cv_uploaded_at = now

    await db.commit()

    return CVResponse(
        fileName=saved_file_name,
        uploadedAt=now.isoformat(),
    )

async def delete_cv(db: AsyncSession, user_id: uuid.UUID) -> dict:
    res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if profile and profile.cv_file_name:
        delete_stored_file(profile.cv_file_name)
        profile.cv_file_name = None
        profile.cv_uploaded_at = None
        await db.commit()

    return {"success": True}

async def get_badges(db: AsyncSession, user_id: uuid.UUID) -> list[BadgeItem]:
    stmt = (
        select(
            Badge.id,
            Badge.name,
            Badge.description,
            Badge.icon,
            Badge.tier,
            Badge.sort_order,
            UserBadge.earned,
            UserBadge.earned_at,
        )
        .outerjoin(UserBadge, (UserBadge.badge_id == Badge.id) & (UserBadge.user_id == user_id))
        .order_by(Badge.sort_order.asc(), Badge.id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    badges = []
    for r in rows:
        tier_val = r.tier.value if hasattr(r.tier, "value") else str(r.tier)
        badges.append(
            BadgeItem(
                id=r.id,
                name=r.name,
                description=r.description,
                icon=r.icon,
                tier=tier_val,
                earned=bool(r.earned),
                earned_at=r.earned_at,
            )
        )
    return badges
