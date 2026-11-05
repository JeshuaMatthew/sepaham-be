import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.profile.schemas import ProfileResponse, ProfileUpdateRequest
from src.app.shared.Services.storage import process_image_url, delete_stored_file

async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> ProfileResponse:
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")

    res_p = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res_p.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return ProfileResponse(
        id=str(user.id),
        avatar_url=profile.avatar_url or "",
        name=user.name,
        username=profile.username or "",
        university=profile.university or "",
        batch=profile.batch,
        role=profile.role_title or "",
        role_emoji=profile.role_emoji or "",
        bio=profile.bio or "",
        location=profile.location or "",
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

    if req.name is not None:
        user.name = req.name.strip()

    if req.avatar_url is not None:
        old_avatar = profile.avatar_url
        new_avatar = await process_image_url(req.avatar_url)
        profile.avatar_url = new_avatar or ""
        if old_avatar and old_avatar != profile.avatar_url and "/uploads/" in old_avatar:
            delete_stored_file(old_avatar)

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
        id=str(user.id),
        avatar_url=profile.avatar_url or "",
        name=user.name,
        username=profile.username or "",
        university=profile.university or "",
        batch=profile.batch,
        role=profile.role_title or "",
        role_emoji=profile.role_emoji or "",
        bio=profile.bio or "",
        location=profile.location or "",
    )
