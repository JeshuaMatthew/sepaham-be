"""
Otorisasi endpoint chat.

Tiga hal yang dulu salah dan dikunci di sini:

1. `GET /api/channels/{id}/messages` dipanggil tanpa `CurrentUser` sama sekali.
   Id channel di-seed pendek dan tertebak ("general", "loker", "tanya-anonim"),
   jadi siapa pun bisa membaca riwayat — termasuk channel anonim yang
   tujuannya justru menyembunyikan identitas.
2. `post_channel_message` hanya memastikan channel-nya ada, tidak mengecek
   keanggotaan server. User bisa menulis ke server mana pun.
3. Endpoint AI memakai `OptionalCurrentUser`, jadi siapa pun tanpa token bisa
   menghabiskan kuota LLM.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.app.core.security import create_access_token
from src.app.main import app

# Akun seed yang merupakan anggota server "itb", dan bukan anggota "ui".
MEMBER_EMAIL = "siti@sepaham.local"
OUTSIDER_EMAIL = "budi@sepaham.local"

ITB_CHANNEL = "general"
UI_CHANNEL = "ui-general"

# user_low/user_high di direct_conversations harus <= dari user_high. Semua
# fixture user seed dibuat lewat seeder yang sudah memenuhi aturan itu.
JOINED_BY = {
    "siti@sepaham.local": "e1000000-0000-0000-0000-000000000001",
    "budi@sepaham.local": "e1000000-0000-0000-0000-000000000002",
    "nadia@sepaham.local": "e1000000-0000-0000-0000-000000000003",
    "rian@sepaham.local": "e1000000-0000-0000-0000-000000000004",
    "salsa@sepaham.local": "e1000000-0000-0000-0000-000000000005",
    "kevin@sepaham.local": "e1000000-0000-0000-0000-000000000006",
    "seed-faculty@sepaham.local": "e1000000-0000-0000-0000-000000000007",
}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    res = await client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, res.text
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_channel_messages_require_token():
    async with _client() as ac:
        res = await ac.get(f"/api/channels/{ITB_CHANNEL}/messages")
        assert res.status_code == 401, f"channel dibaca tanpa token: {res.text}"


@pytest.mark.anyio
async def test_channel_messages_reject_invalid_token():
    async with _client() as ac:
        res = await ac.get(
            f"/api/channels/{ITB_CHANNEL}/messages",
            headers={"Authorization": "Bearer bukan-token"},
        )
        assert res.status_code == 401, res.text


@pytest.mark.anyio
async def test_channel_messages_forbidden_for_non_member():
    """Anggota server "itb" tidak boleh membaca channel server "ui"."""
    async with _client() as ac:
        headers = await _auth_headers(ac, MEMBER_EMAIL)
        res = await ac.get(f"/api/channels/{UI_CHANNEL}/messages", headers=headers)
        assert res.status_code in (403, 404), (
            f"cross-server read tidak ditolak: {res.status_code} {res.text}"
        )


@pytest.mark.anyio
async def test_post_channel_message_forbidden_for_non_member():
    async with _client() as ac:
        headers = await _auth_headers(ac, MEMBER_EMAIL)
        res = await ac.post(
            f"/api/channels/{UI_CHANNEL}/messages",
            headers=headers,
            json={"text": "menembak ke server lain"},
        )
        assert res.status_code in (403, 404), res.text


@pytest.mark.anyio
async def test_ai_assist_requires_token():
    async with _client() as ac:
        res = await ac.post("/api/ai/assist", json={"message": "halo"})
        assert res.status_code == 401, f"AI anonim diterima: {res.text}"


@pytest.mark.anyio
async def test_ai_generate_requires_token():
    async with _client() as ac:
        res = await ac.post("/api/ai/generate", json={"message": "halo"})
        assert res.status_code == 401, f"AI anonim diterima: {res.text}"


@pytest.mark.anyio
async def test_forged_token_with_known_subject_is_rejected():
    """Token yang ditandatangani dengan `JWT_SECRET` lama harus ditolak.

    Yang diuji: `settings.JWT_SECRET` sekarang wajib diisi dari env dan tidak
    punya default di source. Kalau suatu saat ada yang mengembalikan default
    hardcoded lagi, token HMAC buatan sendiri akan lolos.
    """
    import jwt as pyjwt

    forged = pyjwt.encode(
        {"sub": JOINED_BY[MEMBER_EMAIL], "role": "student", "exp": 4102444800},
        "dev-secret-change-me",
        algorithm="HS256",
    )

    async with _client() as ac:
        res = await ac.get(
            f"/api/channels/{ITB_CHANNEL}/messages",
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert res.status_code == 401, f"token HMAC buatan sendiri diterima: {res.text}"
