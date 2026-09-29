import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.app.modules.catalog.entity import (
    Role,
    InternshipContact,
    DevQuote,
    AiInternship,
    LofiTrack,
    UserPreference,
)
from src.app.modules.badges.entity import Badge
from src.app.modules.github.entity import GithubStats
from src.app.modules.catalog.schemas import (
    RoleItem,
    RolesResponse,
    InternshipContactItem,
    InternshipsResponse,
    DevQuoteItem,
    AiInternshipItem,
    AiNudgeItem,
    AiFeedResponse,
    LofiTrackItem,
    LofiTracksResponse,
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

async def get_badges_catalog(db: AsyncSession) -> dict:
    """
    Katalog badge yang tersedia.

    Field `earned` dihapus. Endpoint ini tidak butuh autentikasi, jadi tidak
    bisa tahu badge milik siapa — tapi field itu selalu `False`, dan UI
    memakainya untuk menampilkan status "belum didapat". Hasilnya setiap user
    melihat semua badge sebagai belum pernah dimiliki, dan tidak ada bedanya
    dengan benar-benar belum memilikinya.

    Badge milik user ada di `GET /api/profile/badges`, yang memang per-user.
    """
    res = await db.execute(select(Badge).order_by(Badge.sort_order.asc()))
    badges = res.scalars().all()
    return {
        "badges": [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description or "",
                "icon": b.icon or "",
                "tier": b.tier.value if hasattr(b.tier, "value") else str(b.tier),
            }
            for b in badges
        ]
    }

async def get_internships(db: AsyncSession) -> InternshipsResponse:
    res = await db.execute(select(InternshipContact).order_by(InternshipContact.id.asc()))
    contacts = res.scalars().all()
    return InternshipsResponse(
        contacts=[
            InternshipContactItem(
                id=c.id,
                company=c.company,
                emoji=c.emoji or "",
                position=c.position,
                roleId=c.role_id,
                location=c.location or "",
                type=c.type or "",
                pic=c.pic or "",
                contact=c.contact or "",
                note=c.note,
            )
            for c in contacts
        ]
    )

async def _build_streak_nudge(db: AsyncSession, user_id: uuid.UUID) -> AiNudgeItem:
    """
    Bangun kartu streak dari data GitHub user yang sebenarnya.

    Sebelumnya `AiNudgeItem()` dipakai tanpa argumen sehingga semua user melihat
    "17-day streak" yang sama, padahal profil mereka melaporkan angka lain
    (mis. `github_stats.current_streak = 7`).
    """
    res = await db.execute(select(GithubStats).where(GithubStats.user_id == user_id))
    stats = res.scalar_one_or_none()

    if stats is None:
        # Tanpa data GitHub tidak ada aksi nyata yang bisa dikerjakan user
        # (tombol "Connect GitHub" sengaja tidak ada di UI), jadi jangan
        # menjanjikan koneksi lewat copy atau CTA.
        return AiNudgeItem(
            title="Belum ada streak",
            message="Belum ada data commit GitHub yang terhubung ke akunmu.",
            streak=0,
            cta="",
        )

    streak = stats.current_streak or 0
    if streak <= 0:
        return AiNudgeItem(
            title="Mulai streak hari ini",
            message="Belum ada commit hari ini. Satu commit saja cukup untuk memulai.",
            streak=0,
        )

    return AiNudgeItem(
        title="Keep your streak alive!",
        message=(
            f"You have committed {streak} days in a row. "
            f"Longest streak: {stats.longest_streak or 0} days."
        ),
        streak=streak,
    )


async def get_ai_feed(db: AsyncSession, user_id: uuid.UUID) -> AiFeedResponse:
    quotes_res = await db.execute(select(DevQuote))
    quotes = quotes_res.scalars().all()

    ai_res = await db.execute(select(AiInternship).order_by(AiInternship.match_percent.desc()))
    internships = ai_res.scalars().all()

    return AiFeedResponse(
        quotes=[DevQuoteItem(text=q.text, author=q.author) for q in quotes],
        nudge=await _build_streak_nudge(db, user_id),
        internships=[
            AiInternshipItem(
                id=i.id,
                company=i.company,
                emoji=i.emoji or "",
                role=i.role,
                location=i.location or "",
                type=i.type or "",
                matchPercent=i.match_percent,
                tags=i.tags or [],
            )
            for i in internships
        ],
    )

async def get_lofi(db: AsyncSession) -> LofiTracksResponse:
    res = await db.execute(select(LofiTrack).order_by(LofiTrack.id.asc()))
    tracks = res.scalars().all()
    return LofiTracksResponse(
        tracks=[
            LofiTrackItem(
                id=t.id,
                title=t.title,
                artist=t.artist or "",
            )
            for t in tracks
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
    )
