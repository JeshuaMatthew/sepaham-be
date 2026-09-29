from src.app.modules.onboarding.services.inference import forward_chaining_match


def test_perfect_match():
    user_facts = {"likes_logic", "knows_python", "knows_sql"}
    rules = [
        {
            "role_id": "data_engineer",
            "conditions": {"likes_logic": True, "knows_python": True, "knows_sql": True},
        },
        {
            "role_id": "ui_designer",
            "conditions": {"prefers_visual": True, "knows_figma": True},
        },
    ]
    res = forward_chaining_match(user_facts, rules)
    assert res["recommended_role"] == "data_engineer"
    assert res["match_percentage"] == 100.0


def test_competing_roles():
    user_facts = {"likes_math", "likes_code"}
    rules = [
        {
            "role_id": "data_scientist",
            "conditions": {"likes_math": True, "likes_code": True},
        },
        {
            "role_id": "backend_dev",
            "conditions": {"likes_code": True, "likes_math": False},
        },
    ]
    res = forward_chaining_match(user_facts, rules)
    assert res["recommended_role"] == "data_scientist"
    assert res["match_percentage"] == 100.0
