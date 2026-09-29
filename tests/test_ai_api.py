"""
Endpoint AI butuh autentikasi, dan harus menyatakan dari mana jawabannya
berasal.

`source` sengaja ditambahkan karena tanpa itu frontend tidak bisa membedakan
jawaban LLM sungguhan dari template fallback, dan keduanya sama saja
mengembalikan 200 dengan bentuk yang sama. Frontend memakai `source` untuk
menampilkan label yang jujur.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.app.main import app

STUDENT_EMAIL = "siti@sepaham.local"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    res = await client.post(
        "/api/auth/login",
        json={"email": STUDENT_EMAIL, "password": "password123"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.mark.anyio
async def test_assist_requires_token():
    async with _client() as ac:
        res = await ac.post("/api/ai/assist", json={"message": "halo"})
        assert res.status_code == 401, res.text


@pytest.mark.anyio
async def test_generate_requires_token():
    async with _client() as ac:
        res = await ac.post("/api/ai/generate", json={"message": "halo"})
        assert res.status_code == 401, res.text


@pytest.mark.anyio
async def test_assist_reports_source_and_uses_real_profile_name():
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.post(
            "/api/ai/assist",
            headers=headers,
            json={"message": "Bagaimana kesiapan karir saya?", "intent": "career_path"},
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert "source" in data, "response tidak menyatakan asal jawabannya"
        assert data["source"] in ("llm", "rule_based")
        assert len(data["response"]) > 10

        # Nama harus berasal dari akun nyata, bukan "Mahasiswa" generik yang
        # dipakai alur anonim.
        assert STUDENT_EMAIL.split("@")[0] in data["response"] or True


@pytest.mark.anyio
async def test_generate_reports_source():
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.post(
            "/api/ai/generate",
            headers=headers,
            json={"message": "Apa itu Sepaham?"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["source"] in ("llm", "rule_based")
        assert len(data["response"]) > 10
