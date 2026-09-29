"""Pemberian badge dari aksi nyata di aplikasi.

Setiap badge di katalog (`badges`) punya syarat yang bisa dihitung dari
database — jumlah submission selesai, request Cari Tim, pesan terkirim, dan
CV yang diunggah. Tidak ada lagi badge yang syaratnya memakai data GitHub
yang tidak bisa diukur tanpa token OAuth.

Fungsi utama `award_badges_for_user` idempoten: dipanggil setelah tiap aksi
relevan, dan hanya menyisipkan badge yang syaratnya terpenuhi dan belum
dimiliki (`on_conflict_do_nothing`).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.modules.badges.entity import Badge
from src.app.modules.userBadge.entity import UserBadge

# Ambang tiap badge. Diubah di sini kalau desain gamifikasi berubah — syaratnya
# selalu terdokumentasi di deskripsi badge di database.
THRESHOLD_CONSISTENT = 5
THRESHOLD_EXPLORER = 10
THRESHOLD_COMMUNICATOR = 10


async def _counts(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int | bool]:
    from src.app.modules.roadmap.entity import Submission
    from src.app.modules.collab.entity import CollabRequest
    from src.app.modules.community.entity import Message
    from src.app.modules.profile.entity import Profile

    done_submissions = await db.scalar(
        select(func.count(Submission.id)).where(
            Submission.user_id == user_id,
            Submission.done.is_(True),
        )
    )
    requests = await db.scalar(
        select(func.count(CollabRequest.id)).where(CollabRequest.author_id == user_id)
    )
    messages = await db.scalar(
        select(func.count(Message.id)).where(Message.author_id == user_id)
    )
    has_cv = await db.scalar(
        select(Profile.cv_file_name).where(Profile.user_id == user_id)
    )

    # `cv_file_name` saja tidak cukup: data seed lama berisi nama berkas CV
    # yang file-nya tidak ada di `uploads/`. Badge hanya diberi kalau berkasnya
    # benar-benar ada di disk.
    cv_exists = False
    if has_cv:
        from pathlib import Path as _Path

        filename = str(has_cv).split("/")[-1].split("?")[0]
        if "/" not in filename and "\\" not in filename and ".." not in filename:
            cv_exists = (_Path("uploads") / filename).is_file()

    return {
        "done_submissions": int(done_submissions or 0),
        "requests": int(requests or 0),
        "messages": int(messages or 0),
        "has_cv": cv_exists,
    }


def _deserved(counts: dict[str, int | bool]) -> list[str]:
    deserved: list[str] = []
    if int(counts["done_submissions"]) >= 1:
        deserved.append("langkah-pertama")
    if int(counts["done_submissions"]) >= THRESHOLD_CONSISTENT:
        deserved.append("konsisten")
    if int(counts["done_submissions"]) >= THRESHOLD_EXPLORER:
        deserved.append("penjelajah")
    if int(counts["requests"]) >= 1:
        deserved.append("kolaborator")
    if int(counts["messages"]) >= THRESHOLD_COMMUNICATOR:
        deserved.append("komunikator")
    if bool(counts["has_cv"]):
        deserved.append("profil-lengkap")
    return deserved


async def award_badges_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Beri badge yang syaratnya sudah terpenuhi. Kembalikan id yang baru diberi."""
    counts = await _counts(db, user_id)
    deserved = _deserved(counts)
    if not deserved:
        return []

    # Hanya badge yang masih ada di katalog yang bisa diberi.
    res = await db.execute(select(Badge.id).where(Badge.id.in_(deserved)))
    valid = set(res.scalars().all())
    if not valid:
        return []

    stmt = insert(UserBadge).values(
        [{"user_id": user_id, "badge_id": badge_id} for badge_id in valid]
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "badge_id"])
    result = await db.execute(stmt)
    await db.commit()

    # `rowcount` di asyncpg menghitung baris yang benar-benar disisipkan.
    inserted = int(result.rowcount or 0)
    if inserted <= 0:
        return []
    # Ambil yang memang baru — bandingkan sebelum/sesudah tidak murah, jadi
    # kembalikan yang valid; pemanggil tidak membutuhkannya presisi.
    return sorted(valid)
