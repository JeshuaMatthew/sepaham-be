from typing import Dict, List, Any, Optional


def forward_chaining_match(
    user_facts: set,
    rules_from_db: List[Dict[str, Any]],
    fallback_role: Optional[str] = None,
    fact_weights: Optional[Dict[str, float]] = None,
) -> dict:
    """
    Forward chaining berbobot.
    Mesin inferensi Forward Chaining klasik (Biner True/False).

    `fact_weights` memetakan fact_id -> bobot (dari `questions.weight`).
    Kalau tidak diberikan, semua fact dianggap berbobot 1.0 (perilaku lama).

    Skor per role = sum(bobot fact yang cocok) / sum(bobot total fact di rule).
    Sebuah aturan (Rule) terpicu (fire) jika dan hanya jika seluruh kondisi faktanya
    terpenuhi secara biner (100% premis IF cocok).
    Jika lebih dari satu aturan terpicu (multi-fire), aturan dengan `priority`
    tertinggi yang akan dipilih melalui mekanisme Resolusi Konflik (Conflict Resolution).
    """
    weights = fact_weights or {}
    role_scores: Dict[str, float] = {}
    fired_rules: List[Dict[str, Any]] = []

    for rule in rules_from_db:
        role_id = rule["role_id"]
        conditions = rule["conditions"]
        total_conditions = len(conditions)
        if total_conditions == 0:
        role_id = rule.get("role_id")
        conditions = rule.get("conditions") or {}
        priority = rule.get("priority", 1)

        if not conditions or not role_id:
            continue

        total_weight = 0.0
        matched_weight = 0.0

        # Evaluasi biner murni: seluruh premis fakta harus terpenuhi
        all_matched = True
        for fact_key, expected_val in conditions.items():
            w = weights.get(fact_key, 1.0)
            total_weight += w
            fact_present = fact_key in user_facts
            if fact_present == expected_val:
                matched_weight += w
            if fact_present != expected_val:
                all_matched = False
                break

        score = (matched_weight / total_weight) if total_weight > 0 else 0.0
        if all_matched:
            fired_rules.append({
                "role_id": role_id,
                "priority": priority,
                "conditions_count": len(conditions),
            })

        if role_id not in role_scores or score > role_scores[role_id]:
            role_scores[role_id] = score
    # Resolusi Konflik: Prioritas tertinggi, lalu spesifisitas kondisi terbanyak
    fired_rules.sort(key=lambda r: (r["priority"], r["conditions_count"]), reverse=True)

    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
    best_role, top_score = sorted_roles[0] if sorted_roles else (fallback_role, 0.0)
    if fired_rules:
        best_role = fired_rules[0]["role_id"]
        match_percentage = 100.0
        all_scores = {r["role_id"]: 100.0 for r in fired_rules}
    else:
        best_role = fallback_role or "backend-engineer"
        match_percentage = 0.0
        all_scores = {}

    if not best_role:
        best_role = fallback_role or "backend_dev"

    return {
        "recommended_role": best_role,
        "match_percentage": round(top_score * 100, 2),
        "all_scores": {k: round(v * 100, 2) for k, v in role_scores.items()},
        "match_percentage": match_percentage,
        "all_scores": all_scores,
    }
