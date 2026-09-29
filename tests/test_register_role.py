"""
Registrasi akun dan privilege escalation.

Inti dari file ini: peran akun tidak boleh bisa dipilih dari sisi klien.
Dulu `RegisterRequest` punya field `role` dan service memakainya apa adanya,
sehingga `POST /api/auth/register {"role": "faculty"}` membuat akun dosen
untuk siapa saja yang mengirimnya.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from tests.conftest import TestSessionLocal
from src.app.modules.auth.entity import User
from src.app.main import app

# Tes ini memanggil API sungguhan terhadap database yang sama dengan aplikasi,
# jadi setiap user yang dibuat harus dibersihkan. Email-nya memakai prefiks
# yang sama persis, jadi tidak ada yang bisa luput.
TEST_EMAIL_PREFIXES = ("escalation-", "duplikat-", "pendek-")


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def clean_test_users():
    """Buang user tes sebelum dan sesudah tiap test."""
    await _purge()
    yield
    await _purge()


async def _purge() -> None:
    async with TestSessionLocal() as session:
        for prefix in TEST_EMAIL_PREFIXES:
            await session.execute(
                delete(User).where(User.email.like(f"{prefix}%@%")),
            )
        await session.commit()


@pytest.mark.anyio
async def test_register_ignores_client_supplied_role():
    """Role faculty di body harus diabaikan, hasilnya tetap student."""
    email = f"escalation-{uuid.uuid4().hex[:8]}@sepaham.local"
    async with _client() as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "password123",
                "name": "Escalation",
                "role": "faculty",
            },
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["user"]["role"] == "student", (
            f"role dari body dipakai apa adanya: {body['user']['role']}"
        )


@pytest.mark.anyio
async def test_register_rejects_short_password():
    """Password di bawah 8 karakter harus ditolak.

    Validasi pydantic di sini dipetakan jadi 400 oleh
    `validation_exception_handler` di main.py, bukan 422 bawaan FastAPI.
    """
    email = f"pendek-{uuid.uuid4().hex[:8]}@sepaham.local"
    async with _client() as ac:
        res = await ac.post(
            "/api/auth/register",
            json={"email": email, "password": "pendek", "name": "Pendek"},
        )
        assert res.status_code == 400, res.text
        assert "minimal 8 karakter" in res.text


@pytest.mark.anyio
async def test_register_rejects_invalid_email():
    async with _client() as ac:
        res = await ac.post(
            "/api/auth/register",
            json={"email": "bukan-email", "password": "password123", "name": "X"},
        )
        assert res.status_code == 400, res.text


@pytest.mark.anyio
async def test_register_duplicate_email_conflicts():
    email = f"duplikat-{uuid.uuid4().hex[:8]}@sepaham.local"
    async with _client() as ac:
        payload = {
            "email": email,
            "password": "password123",
            "name": "Duplikat",
        }
        first = await ac.post("/api/auth/register", json=payload)
        assert first.status_code == 201, first.text
        second = await ac.post("/api/auth/register", json=payload)
        assert second.status_code == 409, second.text
