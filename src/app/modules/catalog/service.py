import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.app.modules.catalog.entity import (
    Role,
    UserPreference,
)
from src.app.modules.catalog.schemas import (
    RoleItem,
    RolesResponse,
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)

async def get_roles(db: AsyncSession) -> RolesResponse:
    res = await db.execute(select(Role).order_by(Role.sort_order.asc()))
    roles = res.scalars().all()
    return RolesResponse(
        roles=[
            RoleItem(
                id=r.id,
                title=r.title,
                emoji=r.emoji or "",
                tagline=r.tagline or "",
                description=r.description or "",
                accent=r.accent or "",
                matchTags=r.match_tags or [],
                techStack=r.tech_stack or [],
            )
            for r in roles
        ]
    )

async def get_preferences(db: AsyncSession, user_id: uuid.UUID) -> Optional[UserPreferenceResponse]:
    res = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    pref = res.scalar_one_or_none()
    if not pref:
        return None
    return UserPreferenceResponse(
        roleId=pref.role_id,
        roleTitle=pref.role_title or "",
        roleEmoji=pref.role_emoji or "",
        roleScores=pref.role_scores or {},
        roleScores={},
    )

async def upsert_preferences(
    db: AsyncSession, user_id: uuid.UUID, req: UserPreferenceUpdateRequest
) -> UserPreferenceResponse:
    role_id_to_save = req.role_id
    if role_id_to_save:
        role_exists = await db.scalar(select(Role.id).where(Role.id == role_id_to_save))
        if not role_exists:
            role_id_to_save = None

    stmt = insert(UserPreference).values(
        user_id=user_id,
        role_id=role_id_to_save,
        role_title=req.role_title,
        role_emoji=req.role_emoji,
        role_scores=req.role_scores,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "role_id": role_id_to_save,
            "role_title": req.role_title,
            "role_emoji": req.role_emoji,
            "role_scores": req.role_scores,
        },
    ).returning(
        UserPreference.role_id,
        UserPreference.role_title,
        UserPreference.role_emoji,
        UserPreference.role_scores,
    )
    res = await db.execute(stmt)
    await db.commit()
    row = res.one()
    return UserPreferenceResponse(
        roleId=row.role_id,
        roleTitle=row.role_title or "",
        roleEmoji=row.role_emoji or "",
        roleScores=row.role_scores or {},
        roleScores={},
    )
