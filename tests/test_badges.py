"""
Pemberian badge dari aksi nyata.

Yang dikunci file ini:

- Katalog badge lama syaratnya memakai data GitHub yang tidak bisa diukur
  tanpa token OAuth (commit, streak, bahasa, bintang, PR), dan tidak ada kode
  yang pernah memberi badge (`UserBadge(` tidak pernah di-instantiate).
  Katalog sekarang berisi badge yang syaratnya terukur dari database aplikasi:
  submission selesai, request Cari Tim, pesan terkirim, CV diunggah.
- `award_badges_for_user` idempoten: dipanggil dua kali tidak membuat baris
  ganda.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from tests.conftest import TestSessionLocal
from src.app.modules.auth.entity import User
from src.app.modules.badges.service import award_badges_for_user
from src.app.modules.userBadge.entity import UserBadge
from src.app.main import app


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def temp_user():
    """User sementara yang dihapus lagi setelah tes (cascade ikut buang badge)."""
    email = f"badge-{uuid.uuid4().hex[:8]}@sepaham.local"
    async with _client() as ac:
        res = await ac.post(
            "/api/auth/register",
            json={"email": email, "password": "password123", "name": "Badge"},
        )
        assert res.status_code == 201, res.text
        user_id = res.json()["user"]["id"]
        token = res.json()["token"]
    yield {"id": user_id, "email": email, "token": token}
    async with TestSessionLocal() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.commit()


async def _earned_badges(user_id: str) -> set[str]:
    async with TestSessionLocal() as session:
        res = await session.execute(
            select(UserBadge.badge_id).where(UserBadge.user_id == uuid.UUID(user_id))
        )
        return set(res.scalars().all())


@pytest.mark.anyio
async def test_text_submission_awards_langkah_pertama(temp_user):
    """Satu submission teks yang valid memberi badge langkah-pertama."""
    async with _client() as ac:
        headers = {"Authorization": f"Bearer {temp_user['token']}"}
        res = await ac.put(
            "/api/roadmaps/frontend/nodes/javascript/submission",
            headers=headers,
            json={"text": "https://github.com/badge/todo-app"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["done"] is True

    earned = await _earned_badges(temp_user["id"])
    assert "langkah-pertama" in earned, f"badge tidak diberi: {earned}"


@pytest.mark.anyio
async def test_award_is_idempotent(temp_user):
    """Diberi dua kali tetap satu baris (on_conflict_do_nothing)."""
    async with TestSessionLocal() as session:
        user_uuid = uuid.UUID(temp_user["id"])
        first = await award_badges_for_user(session, user_uuid)
        second = await award_badges_for_user(session, user_uuid)

    # User baru tanpa aksi: tidak ada yang diberi.
    assert first == []
    assert second == []

    earned = await _earned_badges(temp_user["id"])
    assert earned == set()


@pytest.mark.anyio
async def test_existing_progress_awards_matching_badges():
    """User yang sudah punya 8 submission selesai dapat langkah-pertama dan konsisten."""
    async with TestSessionLocal() as session:
        res = await session.execute(select(User.id).where(User.email == "siti@sepaham.local"))
        siti_id = res.scalar_one()
        awarded = await award_badges_for_user(session, siti_id)

    earned = await _earned_badges(str(siti_id))
    assert "langkah-pertama" in earned
    assert "konsisten" in earned
    assert awarded, "tidak ada badge baru yang dilaporkan"

    # Bersihkan supaya database kembali seperti semula.
    async with TestSessionLocal() as session:
        await session.execute(delete(UserBadge).where(UserBadge.user_id == siti_id))
        await session.commit()
