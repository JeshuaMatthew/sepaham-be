from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.modules.faculty.schemas import RoleResponse, RoleUpsertRequest

# ===== Role Management (F#06) =====

async def list_roles(db: AsyncSession) -> list[RoleResponse]:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).order_by(Role.sort_order)
    result = await db.execute(stmt)
    roles = result.scalars().all()

    return [
        RoleResponse(
            id=r.id,
            title=r.title,
            emoji=r.emoji or "",
            tagline=r.tagline or "",
            description=r.description or "",
            accent=r.accent or "",
        )
        for r in roles
    ]


async def create_role(db: AsyncSession, req: RoleUpsertRequest) -> RoleResponse:
    from src.app.modules.catalog.entity import Role

    role = Role(
        id=req.title.lower().replace(" ", "-").replace("/", "-"),
        title=req.title,
        emoji=req.emoji or "",
        tagline=req.tagline or "",
        description=req.description or "",
        accent=req.accent or "",
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        title=role.title,
        emoji=role.emoji or "",
        tagline=role.tagline or "",
        description=role.description or "",
        accent=role.accent or "",
    )


async def update_role(db: AsyncSession, role_id: str, req: RoleUpsertRequest) -> RoleResponse:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role tidak ditemukan",
        )

    role.title = req.title
    role.emoji = req.emoji or ""
    role.tagline = req.tagline or ""
    role.description = req.description or ""
    role.accent = req.accent or ""
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        title=role.title,
        emoji=role.emoji or "",
        tagline=role.tagline or "",
        description=role.description or "",
        accent=role.accent or "",
    )


async def delete_role(db: AsyncSession, role_id: str) -> None:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role tidak ditemukan",
        )

    await db.delete(role)
    await db.commit()
