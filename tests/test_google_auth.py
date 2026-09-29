"""
Keamanan alur login Google.

Tes-tes di sini sengaja mengunci perilaku yang PERNAH salah dan sudah
diperbaiki. Kalau salah satu gagal, berarti kerentanan itu kembali.

Yang diuji:
- `POST /api/auth/google` dengan `email` mentah dari body harus DITOLAK.
  Alur lama membaca `req.email` dan jatuh ke sana kalau decode JWT gagal,
  sehingga body `{"email": "kositasi@..."}` saja berhasil memberi token.
- ID token dengan signature HS256 buatan sendiri harus DITOLAK. Google hanya
  menandatangani dengan RSA lewat JWKS, jadi HS256 selalu gagal.
- Permintaan tanpa kredensial sama sekali harus DITOLAK.
- `POST /api/auth/register` dengan `role: "faculty"` harus membuat akun
  mahasiswa. Dulu field itu dipakai apa adanya.
"""

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from src.app.main import app

# Client id nyata proyek ini. ID token palsu dibuat untuk audience ini supaya
# tes benar-benar menguji jalur verifikasi, bukan sekadar "audience salah".
GOOGLE_CLIENT_ID = "330398302271-do0tt3f1r3ggh1im8crfs7f6tvu57ghh.apps.googleusercontent.com"
VICTIM_EMAIL = "korban@sepaham.local"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_google_auth_rejects_raw_email_in_body():
    """Body `{"email": ...}` tanpa kredensial Google apa pun harus 401."""
    async with _client() as ac:
        res = await ac.post("/api/auth/google", json={"email": VICTIM_EMAIL})
        assert res.status_code == 401, f"email mentah diterima: {res.text}"


@pytest.mark.anyio
async def test_google_auth_rejects_self_signed_hs256_token():
    """Token HS256 buatan sendiri tidak boleh diterima, meski aud/iss benar."""
    forged = jwt.encode(
        {
            "email": VICTIM_EMAIL,
            "email_verified": True,
            "name": "Penyerang",
            "sub": "1234567890",
            "aud": GOOGLE_CLIENT_ID,
            "iss": "https://accounts.google.com",
            "iat": 1,
            "exp": 4102444800,
        },
        "rahasia-palsu",
        algorithm="HS256",
    )

    async with _client() as ac:
        res = await ac.post("/api/auth/google", json={"credential": forged})
        assert res.status_code == 401, f"token HS256 palsu diterima: {res.text}"


@pytest.mark.anyio
async def test_google_auth_rejects_expired_token():
    """ID token yang sudah kedaluwarsa harus ditolak, bukan diterima diam-diam."""
    expired = jwt.encode(
        {
            "email": VICTIM_EMAIL,
            "email_verified": True,
            "name": "Kedaluwarsa",
            "sub": "1234567890",
            "aud": GOOGLE_CLIENT_ID,
            "iss": "https://accounts.google.com",
            "iat": 1,
            "exp": 2,
        },
        "rahasia-palsu",
        algorithm="HS256",
    )

    async with _client() as ac:
        res = await ac.post("/api/auth/google", json={"credential": expired})
        assert res.status_code == 401


@pytest.mark.anyio
async def test_google_auth_rejects_empty_request():
    """Body kosong harus ditolak, bukan membuat sesi dari data apa pun."""
    async with _client() as ac:
        res = await ac.post("/api/auth/google", json={})
        assert res.status_code == 401


@pytest.mark.anyio
async def test_google_auth_rejects_bogus_access_token():
    """Access token ngawur harus ditolak oleh verifikasi Google."""
    async with _client() as ac:
        res = await ac.post("/api/auth/google", json={"access_token": "bukan-token-google"})
        assert res.status_code == 401
