from typing import Dict, List, Any, Optional


def forward_chaining_match(
    user_facts: set,
    rules_from_db: List[Dict[str, Any]],
    fallback_role: Optional[str] = None,
    fact_weights: Optional[Dict[str, float]] = None,
) -> dict:
    """
    Forward chaining berbobot.

    `fact_weights` memetakan fact_id -> bobot (dari `questions.weight`).
    Kalau tidak diberikan, semua fact dianggap berbobot 1.0 (perilaku lama).

    Skor per role = sum(bobot fact yang cocok) / sum(bobot total fact di rule).
    """
    weights = fact_weights or {}
    role_scores: Dict[str, float] = {}

    for rule in rules_from_db:
        role_id = rule["role_id"]
        conditions = rule["conditions"]
        total_conditions = len(conditions)
        if total_conditions == 0:
            continue

        total_weight = 0.0
        matched_weight = 0.0

        for fact_key, expected_val in conditions.items():
            w = weights.get(fact_key, 1.0)
            total_weight += w
            fact_present = fact_key in user_facts
            if fact_present == expected_val:
                matched_weight += w

        score = (matched_weight / total_weight) if total_weight > 0 else 0.0

        if role_id not in role_scores or score > role_scores[role_id]:
            role_scores[role_id] = score

    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
    best_role, top_score = sorted_roles[0] if sorted_roles else (fallback_role, 0.0)

    if not best_role:
        best_role = fallback_role or "backend_dev"

    return {
        "recommended_role": best_role,
        "match_percentage": round(top_score * 100, 2),
        "all_scores": {k: round(v * 100, 2) for k, v in role_scores.items()},
    }
