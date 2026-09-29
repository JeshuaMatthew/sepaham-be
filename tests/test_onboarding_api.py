import pytest
from httpx import ASGITransport, AsyncClient
from src.app.main import app


@pytest.mark.anyio
async def test_full_onboarding_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fetch pillars
        pillars_res = await ac.get("/api/v1/onboarding/pillars")
        assert pillars_res.status_code == 200
        pillars = pillars_res.json()
        assert len(pillars) >= 5

        # 2. Analyze essay
        essay_text = (
            "Saya sangat tertarik dengan perancangan arsitektur backend, REST API, "
            "dan database relational PostgreSQL serta optimasi query menggunakan Python."
        )
        essay_res = await ac.post("/api/v1/onboarding/analyze-essay", json={"essay": essay_text})
        assert essay_res.status_code == 200
        essay_data = essay_res.json()
        assert "session_id" in essay_data
        session_id = essay_data["session_id"]
        assert len(essay_data["suggested_pillars"]) >= 1

        # 3. Get questions for pillar
        pillar_id = essay_data["suggested_pillars"][0]["id"]
        q_res = await ac.get(f"/api/v1/onboarding/questions?pillar={pillar_id}")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert len(q_data["questions"]) > 0

        # 4. Evaluate answers
        first_q = q_data["questions"][0]
        eval_payload = {
            "session_id": session_id,
            "pillar_id": pillar_id,
            "answers": [{"fact_id": first_q["fact_id"], "value": True}],
        }
        eval_res = await ac.post("/api/v1/onboarding/evaluate", json=eval_payload)
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert "recommended_role" in eval_data
        assert "roadmap_slug" in eval_data
        assert "match_percentage" in eval_data
