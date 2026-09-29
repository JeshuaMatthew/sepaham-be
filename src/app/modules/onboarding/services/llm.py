"""
Klasifikasi esai onboarding ke pilar IT.

Dua jalur, dan keduanya perlu tahu mana yang dipakai:

1. LLM sungguhan, kalau `OPENAI_API_KEY` terpasang.
2. Pencocokan keyword, kalau tidak.

Jalur kedua existed hampir selalu, bukan kasus tepi: `OPENAI_API_KEY` tidak
pernah ada di `.env` maupun `.env.example`, jadi semua user sebenarnya dapat
hasil pencocokan keyword. Yang membuatnya tidak terlihat: `confidence_score`
selalu `0.88` dan `summary_reason` kalimat tetap. Dua esai yang sama sekali
berbeda menghasilkan "88% keyakinan" dan kalimat yang identik.

Di bawah ini confidence dihitung dari bukti yang benar-benar diamati, dan
responsnya menyatakan dari mana asalnya lewat `method`.
"""

import os
import re
from typing import List

from src.app.core.config import settings
from src.app.modules.onboarding.schemas import LLMAnalysisResponse

VALID_PILLARS = [
    "software_dev",
    "data_ai",
    "infra_security",
    "design_ux",
    "tech_management",
]

PILLAR_KEYWORDS = {
    "software_dev": [
        "coding", "programming", "developer", "backend", "frontend", "fullstack",
        "react", "vue", "javascript", "typescript", "python", "golang", "java",
        "api", "database", "web", "mobile", "android", "ios", "flutter", "aplikasi",
        "software", "arsitektur", "algoritma", "bug", "git", "framework"
    ],
    "data_ai": [
        "data", "analyst", "science", "scientist", "machine learning", "deep learning",
        "model", "dataset", "sql", "analytics", "statistics", "statistika", "prediksi",
        "matematika", "pandas", "tableau", "bi", "visualisasi data", "nlp", "llm",
        "kecerdasan buatan", "machine", "pembelajaran mesin"
    ],
    "infra_security": [
        "network", "jaringan", "security", "keamanan", "cyber", "hacker", "pentest",
        "cloud", "aws", "gcp", "azure", "docker", "kubernetes", "devops", "linux",
        "sysadmin", "server", "firewall", "vulnerability", "monitoring", "ci/cd"
    ],
    "design_ux": [
        "ui", "ux", "design", "desain", "figma", "visual", "wireframe", "prototype",
        "user research", "interaksi", "estetika", "antarmuka", "layout", "user experience",
        "animasi", "creative", "kreatif", "grafis"
    ],
    "tech_management": [
        "product", "project", "management", "manajemen", "scrum", "agile", "lead",
        "leader", "komunikasi", "bisnis", "strategi", "roadmap", "stakeholder",
        "planning", "prioritas", "koordinasi", "mvp"
    ],
}

# Kata yang biasanya dipakai untuk menyebut AI. Sengaja TIDAK ada "ai" polos:
# `if "ai" in text` cocok dengan "saya", "detail", dan "lain" sehingga hampir
# semua esai Bahasa Indonesia ikut masuk pilar data_ai. Pola di bawah memakai
# batas kata supaya hanya cocok dengan kata utuh.
AI_KEYWORDS = [
    r"\bai\b",
    r"\bml\b",
    r"\ba\.i\.?",
    r"artificial intelligence",
    r"kecerdasan buatan",
]

TRAIT_RULES = [
    ("Analytical Thinking", [r"analis", r"logika", r"problem", r"statistik", r"riset", r"data"]),
    ("Creative & Visual", [r"kreatif", r"visual", r"desain", r"estetika", r"animasi", r"kreativ"]),
    ("Leadership & Collaboration", [r"komunikasi", r"\btim\b", r"\blead", r"kolaborasi"]),
    ("System Thinking", [r"sistem", r"arsitektur", r"infrastruktur", r"skala", r"scale"]),
]

# Kalau pencarian keyword mencapai angka ini, esainya dianggap spesifik dan
# confidence dihitung penuh. Menormalkan begini membuat dua keyword dari
# enam puluh tidak menghasilkan confidence 3%.
_STRONG_MATCH_THRESHOLD = 6


def sanitize_essay(essay_text: str) -> str:
    """
    Redaksi pola prompt-injection yang mudah dikenali.

    Penting untuk diketahui: ini BUKAN perlindungan. Lima regex
    case-insensitive tidak akan menahan prompt injection, dan nama fungsi
    `sanitize` di jalur ini menciptakan ilusi aman. Yang benar-benar melindungi
    adalah perancangan prompt: instruksi dan konteks yang eksplisit, plus
    batasan skema keluaran. Itu tugas perancangan prompt, bukan regex.
    Fungsi ini tetap dipertahankan sebagai penyaringan kasar terhadap
    percobaan yang paling Gamblang, dengan komentar ini sebagai pengingat.
    """
    adversarial_patterns = [
        r"ignore (all )?previous instructions",
        r"forget (all )?rules",
        r"system prompt",
        r"return role:",
        r"new instructions",
    ]
    cleaned = essay_text
    for pattern in adversarial_patterns:
        cleaned = re.sub(pattern, "[redacted]", cleaned, flags=re.IGNORECASE)
    return cleaned


def _keyword_hits(text: str, keywords: List[str]) -> int:
    """Hitung keyword yang benar-benar muncul sebagai kata utuh.

    Semua keyword dikompilasi jadi `\b...\b` supaya "ai" tidak cocok dengan
    "saya", dan "ui" tidak cocok dengan "kuis".
    """
    hits = 0
    for keyword in keywords:
        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
        if re.search(pattern, text):
            hits += 1
    return hits


def _score_pillars(text: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for pillar, keywords in PILLAR_KEYWORDS.items():
        score = _keyword_hits(text, keywords)
        if pillar == "data_ai":
            score += _keyword_hits(text, AI_KEYWORDS)
        scores[pillar] = score
    return scores


def _detect_traits(text: str) -> list[str]:
    """Traits hanya diisi dari bukti. Tidak ada nilai cadangan."""
    traits: list[str] = []
    for name, patterns in TRAIT_RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                traits.append(name)
                break
    return traits


def _build_summary(top_pillars: list[str], matched: dict[str, list[str]]) -> str:
    """Ringkasan yang menyebut kata yang benar-benar ditemukan."""
    if not top_pillars:
        return "Tidak ada kecocokan pilar yang cukup kuat pada esai ini."

    detail = matched.get(top_pillars[0], [])
    if not detail:
        return f"Pilar teratas: {top_pillars[0]}."

    shown = ", ".join(detail[:5])
    return f"Banyak kata kunci pilar {top_pillars[0]} ditemukan: {shown}."


def heuristic_analyze(essay_text: str) -> LLMAnalysisResponse:
    """Klasifikasi berbasis pencocokan keyword.

    `confidence_score` dihitung dari rasio keyword yang cocok terhadap total
    keyword yang diperiksa, jadi esai yang samar mendapat angka rendah dan
    esai yang spesifik mendapat angka tinggi. Nilai ini bukan probabilitas,
    dan `method="keyword"`ADATAPurpose supaya UI bisa mengatakannya.
    """
    text = essay_text.lower()
    scores = _score_pillars(text)

    # Simpan keyword mana yang cocok, untuk ringkasan dan traits.
    matched: dict[str, list[str]] = {}
    for pillar, keywords in PILLAR_KEYWORDS.items():
        found = [kw for kw in keywords if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text)]
        if pillar == "data_ai":
            found += [m.group(0) for m in (re.search(p, text) for p in AI_KEYWORDS) if m]
        if found:
            matched[pillar] = found

    total_keywords = sum(len(v) for v in PILLAR_KEYWORDS.values()) + len(AI_KEYWORDS)
    total_hits = sum(scores.values())

    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    top_pillars = [pillar for pillar, score in ranked if score > 0][:2]

    if not top_pillars:
        # Tidak adakeyword yang cocok. Ini jawaban yang jujur, bukan tebakan
        # "software_dev" dengan keyakinan 88%.
        return LLMAnalysisResponse(
            selected_pillars=[],
            confidence_score=0.0,
            detected_traits=_detect_traits(text),
            summary_reason="Esai ini belum menyebut bidang IT tertentu. Jawab dengan sedikit lebih detail.",
            method="keyword",
        )

    # Confidence dibatasi oleh seberapa spesifik pencocokannya. Satu keyword
    # saja tidakarrants keyakinan tinggi meski rasio mentahnya besar.
    if total_hits >= _STRONG_MATCH_THRESHOLD:
        ratio = min(1.0, total_hits / _STRONG_MATCH_THRESHOLD)
    else:
        ratio = total_hits / _STRONG_MATCH_THRESHOLD

    # Confidence juga naik kalau hanya satu pilar yang dominan.
    top_score = ranked[0][1]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    dominance = (top_score - runner_up) / top_score if top_score else 0.0
    confidence = round(min(1.0, ratio * 0.7 + dominance * 0.3), 3)

    return LLMAnalysisResponse(
        selected_pillars=top_pillars,
        confidence_score=confidence,
        detected_traits=_detect_traits(text),
        summary_reason=_build_summary(top_pillars, matched),
        method="keyword",
    )


def analyze_essay_with_llm(essay_text: str) -> LLMAnalysisResponse:
    """Analisis esai memakai LLM kalau bisa, kalau tidak pakai keyword.

    Kegagalan LLM tidak diam-diam diganti hasil keyword tanpa jejak:
    `method` pada respons menunjukkan jalurnya, jadi frontend bisa
    menampilkan label yang benar.
    """
    cleaned_essay = sanitize_essay(essay_text)
    api_key = getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY")

    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            system_prompt = f"""
            Kamu adalah konsultan karir IT Senior. Analisis essay pengguna dan klasifikasikan
            mereka ke maksimal 2 dari 5 pilar IT berikut:
            {VALID_PILLARS}.
            Ekstrak juga sifat bawaan mereka (traits).
            Wajib hanya memilih pilar dari daftar resmi tersebut.
            """
            response = client.beta.chat.completions.parse(
                model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": cleaned_essay},
                ],
                response_format=LLMAnalysisResponse,
            )
            parsed = response.choices[0].message.parsed
            if parsed is not None:
                valid = [p for p in parsed.selected_pillars if p in VALID_PILLARS][:2]
                parsed.selected_pillars = valid
                parsed.method = "llm"
                return parsed
        except Exception:
            # Jatuh ke heuristic. `method` di bawah yang memberi tahu frontend.
            pass

    return heuristic_analyze(cleaned_essay)
