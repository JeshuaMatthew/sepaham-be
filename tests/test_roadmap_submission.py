"""
Penilaian quiz dan upload bukti roadmap, diuji lewat HTTP.

Yang dikunci file ini — semua ini pernah salah dan sekarang sudah diperbaiki:

1. `correctIndex` ikut terkirim ke browser, jadi seluruh penilaian bisa
   dilakukan di client dan hasilnya tidak dapat dipercaya.
2. `SubmissionUpsertRequest` menerima `score` dan `done` dari client, dan
   service menyimpannya apa adanya. `{"score": 100, "done": true}` membuka
   node tanpa menjawab satu pun soal.
3. Node bertipe `text` ditandai selesai tanpa isinya.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from tests.conftest import TestSessionLocal
from src.app.modules.roadmap.entity import Submission
from src.app.main import app

STUDENT_EMAIL = "budi@sepaham.local"

# `html-css` punya dua soal dengan kunci q1=1 dan q2=1, passingScore 50.
QUIZ_NODE = "html-css"
TEXT_NODE = "javascript"

CORRECT_ANSWERS = {"q1": 1, "q2": 1}
WRONG_ANSWERS = {"q1": 0, "q2": 0}

_CLEANED_NODES = (QUIZ_NODE, TEXT_NODE)


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    res = await client.post(
        "/api/auth/login",
        json={"email": STUDENT_EMAIL, "password": "password123"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


async def _purge_test_submissions() -> None:
    async with TestSessionLocal() as session:
        await session.execute(
            delete(Submission).where(
                Submission.roadmap_id == "frontend",
                Submission.node_key.in_(_CLEANED_NODES),
            )
        )
        await session.commit()


@pytest.fixture(autouse=True)
async def clean_submission():
    await _purge_test_submissions()
    yield
    await _purge_test_submissions()


@pytest.mark.anyio
async def test_roadmap_payload_has_no_answer_key():
    async with _client() as ac:
        res = await ac.get("/api/roadmaps/frontend")
        assert res.status_code == 200, res.text
        assert "correctIndex" not in res.text, "kunci jawaban masih terkirim ke client"
        # `passingScore` harus tetap ada: UI harus menampilkan ambang yang
        # sama dengan yang ditegakkan server.
        assert "passingScore" in res.text, "ambang kelulusan tidak terkirim ke client"


@pytest.mark.anyio
async def test_faculty_endpoint_includes_answer_key():
    """Editor soal dosen justru butuh melihat kunci jawaban."""
    async with _client() as ac:
        student = await ac.post(
            "/api/auth/login",
            json={"email": STUDENT_EMAIL, "password": "password123"},
        )
        assert student.status_code == 200
        res = await ac.get(
            "/api/faculty/roadmaps/frontend",
            headers={"Authorization": f"Bearer {student.json()['token']}"},
        )
        assert res.status_code == 403, (
            f"mahasiswa bisa ambil kunci jawaban: {res.status_code} {res.text}"
        )

        faculty = await ac.post(
            "/api/auth/login",
            json={"email": "seed-faculty@sepaham.local", "password": "seedfaculty123"},
        )
        assert faculty.status_code == 200, faculty.text
        res2 = await ac.get(
            "/api/faculty/roadmaps/frontend",
            headers={"Authorization": f"Bearer {faculty.json()['token']}"},
        )
        assert res2.status_code == 200, res2.text
        assert "correctIndex" in res2.text, "editor dosen tidak bisa melihat kunci jawaban"


@pytest.mark.anyio
async def test_client_supplied_score_is_rejected():
    """`score` dari client harus ditolak, bukan diam-diam dipakai."""
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.put(
            f"/api/roadmaps/frontend/nodes/{QUIZ_NODE}/submission",
            headers=headers,
            json={"score": 100, "done": True},
        )
        assert res.status_code == 400, (
            f"score dari client tidak ditolak: {res.status_code} {res.text}"
        )


@pytest.mark.anyio
async def test_correct_answers_pass_on_server():
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.put(
            f"/api/roadmaps/frontend/nodes/{QUIZ_NODE}/submission",
            headers=headers,
            json={"quizAnswers": CORRECT_ANSWERS},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["score"] == 100
        assert data["done"] is True
        assert data["scoreDetail"]["correct"] == 2
        assert data["scoreDetail"]["total"] == 2


@pytest.mark.anyio
async def test_wrong_answers_do_not_complete_node():
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.put(
            f"/api/roadmaps/frontend/nodes/{QUIZ_NODE}/submission",
            headers=headers,
            json={"quizAnswers": WRONG_ANSWERS},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["score"] == 0
        assert data["done"] is False, "node selesai padahal jawaban salah semua"


@pytest.mark.anyio
async def test_unknown_node_returns_404():
    async with _client() as ac:
        headers = await _auth_headers(ac)
        res = await ac.put(
            "/api/roadmaps/frontend/nodes/tidak-ada/submission",
            headers=headers,
            json={"quizAnswers": CORRECT_ANSWERS},
        )
        assert res.status_code == 404, res.text


@pytest.mark.anyio
async def test_text_node_completes_only_with_real_text():
    async with _client() as ac:
        headers = await _auth_headers(ac)

        empty = await ac.put(
            f"/api/roadmaps/frontend/nodes/{TEXT_NODE}/submission",
            headers=headers,
            json={"text": "   "},
        )
        assert empty.status_code == 200, empty.text
        assert empty.json()["done"] is False, "node teks selesai tanpa isi"

        filled = await ac.put(
            f"/api/roadmaps/frontend/nodes/{TEXT_NODE}/submission",
            headers=headers,
            json={"text": "https://github.com/budi/todo-app"},
        )
        assert filled.json()["done"] is True
