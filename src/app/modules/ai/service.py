import os
import re
import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.catalog.entity import UserPreference, Role, AiInternship
from src.app.modules.roadmap.entity import Roadmap, RoadmapNode, Submission
from src.app.modules.github.entity import GithubStats
from src.app.modules.ai.schemas import (
    AiAssistRequest,
    AiAssistResponse,
    AiGenerateRequest,
    AiGenerateResponse,
)


async def _gather_user_context(db: AsyncSession, user_id: Optional[uuid.UUID]) -> dict:
    ctx = {
        "user_name": "Mahasiswa",
        "role_title": None,
        "role_id": None,
        "role_tech_stack": [],
        "university": None,
        "github_connected": False,
        "github_stats": None,
        "cv_uploaded": False,
        "roadmap_title": None,
        "roadmap_completed": 0,
        "roadmap_total": 0,
        "strengths": [],
        "internships": [],
    }

    if not user_id:
        # Tanpa user tidak ada yang bisa dicocokkan. Kembalikan apa adanya;
        # jangan isi dengan lowongan yang skornya bukan milik siapa pun.
        ctx["internships"] = []
        return ctx

    # User info
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if user:
        ctx["user_name"] = user.name

    # Profile info
    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        ctx["role_title"] = profile.role_title
        ctx["university"] = profile.university
        ctx["github_connected"] = bool(profile.github_connected)
        ctx["cv_uploaded"] = bool(profile.cv_file_name)

    # Preferences
    pref_res = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    pref = pref_res.scalar_one_or_none()
    pref_role_id = pref.role_id if pref else None
    if pref and not ctx["role_title"]:
        ctx["role_title"] = pref.role_title
    ctx["role_id"] = pref_role_id

    # Tech stack role, dipakai untuk mencocokkan lowongan magang.
    if pref_role_id:
        role_res = await db.execute(select(Role).where(Role.id == pref_role_id))
        role_row = role_res.scalar_one_or_none()
        if role_row:
            ctx["role_tech_stack"] = list(role_row.tech_stack or [])
            if not ctx["role_title"]:
                ctx["role_title"] = role_row.title

    # GitHub Stats
    if ctx["github_connected"]:
        gh_res = await db.execute(select(GithubStats).where(GithubStats.user_id == user_id))
        gh = gh_res.scalar_one_or_none()
        if gh:
            # `total_commits` dan `current_streak` nullable: GitHub tidak
            # menyediakannya lewat API publik. Yang null diteruskan sebagai null,
            # bukan diganti angka.
            ctx["github_stats"] = {
                "commits": gh.total_commits,
                "repos": gh.public_repos or 0,
                "streak": gh.current_streak,
            }

    # Roadmap progress.
    #
    # Hanya roadmap milik role user yang dipakai. Sebelumnya kalau tidak ada
    # yang cocok, jatuh ke `select(Roadmap).limit(1)` tanpa ORDER BY, jadi
    # roadmap yang dipilih adalah baris pertama yang kebetulan dikembalikan
    # Postgres — bisa jadi roadmap orang lain.
    target_rm = None
    if pref_role_id:
        rm_res = await db.execute(select(Roadmap).where(Roadmap.role_id == pref_role_id))
        target_rm = rm_res.scalar_one_or_none()

    if target_rm:
        ctx["roadmap_title"] = target_rm.title
        total_nodes_res = await db.execute(
            select(func.count(RoadmapNode.id)).where(RoadmapNode.roadmap_id == target_rm.id)
        )
        ctx["roadmap_total"] = total_nodes_res.scalar() or 0

        completed_res = await db.execute(
            select(func.count(Submission.id)).where(
                Submission.user_id == user_id,
                Submission.roadmap_id == target_rm.id,
                Submission.done == True,  # noqa: E712
            )
        )
        ctx["roadmap_completed"] = completed_res.scalar() or 0

    # Lowongan magang, dicocokkan ke profil user ini saja.
    pool = await _load_internship_pool(db)
    ctx["internships"] = _match_internships(pool, ctx)

    return ctx


# Kata yang terlalu umum untuk dipakai sebagai bukti kecocokan. "Backend
# Engineer" dan "Frontend Engineer" sama-sama mengandung "engineer", jadi
# kalau kata ini dihitung, dua role yang sama sekali berbeda terlihat cocok.
_GENERIC_ROLE_WORDS = frozenset(
    {
        "engineer",
        "developer",
        "dev",
        "intern",
        "internship",
        "specialist",
        "programmer",
        "staff",
        "lead",
        "analyst",
        "scientist",
        "consultant",
        "specialist",
    }
)


def _significant_words(text: str) -> set[str]:
    return {
        word
        for word in re.split(r"\W+", text.lower())
        if len(word) > 2 and word not in _GENERIC_ROLE_WORDS
    }


def _match_internships(pool: list[dict], ctx: dict) -> list[dict]:
    """Nilai kecocokan lowongan terhadap profil user.

    `ai_internships.match_percent` di database adalah angka seed yang sama untuk
    semua orang, jadi tidak bisa dipakai sebagai "kecocokan". Di sini dihitung
    dari hal yang benar-benar diketahui tentang user: nama role-nya dan tech
    stack role tersebut, dibandingkan dengan `tags` lowongan dan nama role-nya.

    Tanpa role yang diketahui, hasilnya kosong. Itu lebih jujur daripada
    menampilkan lowongan dengan persentase yang bukan milik siapa pun.
    """
    title = (ctx.get("role_title") or "").strip()
    stack = {t.strip().lower() for t in (ctx.get("role_tech_stack") or []) if t.strip()}
    if not title and not stack:
        return []

    title_words = _significant_words(title)

    scored: list[tuple[int, dict]] = []
    for intern in pool:
        tags = {t.strip().lower() for t in (intern.get("tags") or [])}
        intern_words = _significant_words(intern.get("role") or "")

        # Dua komponen: overlap tech stack, dan kesamaan kata nama role.
        stack_overlap = len(stack & tags)
        title_overlap = len(title_words & intern_words)

        # Tech stack dianggap lebih kuat karena lebih spesifik.
        score = stack_overlap * 12 + title_overlap * 8
        if score <= 0:
            continue

        scored.append(
            (
                score,
                {
                    "company": intern["company"],
                    "role": intern["role"],
                    "location": intern["location"],
                    "match": min(100, score),
                    "matched_skills": sorted(stack & tags),
                },
            )
        )

    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored[:3]]


async def _load_internship_pool(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(AiInternship))
    return [
        {
            "id": row.id,
            "company": row.company,
            "role": row.role,
            "location": row.location,
            "tags": list(row.tags or []),
        }
        for row in res.scalars().all()
    ]


def _generate_rule_based_fallback(message: str, intent: str, ctx: dict) -> str:
    """
    Jawaban cadangan saat LLM tidak tersedia.

    Aturannya: hanya menyebut fakta yang benar-benar ada di `ctx`. Tidak ada
    skor gabungan yang dikarang. Sebelumnya di sini ada
    `readiness = rm_pct * 0.4 + (50 if gh) * 0.3 + (70 if cv) * 0.3` yang
    menghasilkan klaim "Job-ready" dari angka yang tidak pernah diukur, dan
    `role` yang jatuh ke "Software Engineer" kalau profil kosong.
    """
    q = message.lower()
    name = ctx["user_name"]
    role = ctx["role_title"]
    rm_completed = ctx["roadmap_completed"]
    rm_total = ctx["roadmap_total"]
    rm_pct = int((rm_completed / rm_total * 100)) if rm_total > 0 else 0
    gh = ctx["github_stats"]
    cv = ctx["cv_uploaded"]

    # Baris fakta, dibangun hanya dari data yang ada.
    facts: list[str] = []
    if ctx["roadmap_title"]:
        facts.append(
            f"• **Roadmap {ctx['roadmap_title']}:** {rm_completed} dari {rm_total} materi selesai ({rm_pct}%)."
        )
    else:
        facts.append("• **Roadmap:** belum ada. Selesaikan onboarding dulu supaya kami tahu arah belajarmu.")
    if gh:
        bits = [f"{gh['repos']} repo publik"]
        if gh["commits"] is not None:
            bits.insert(0, f"{gh['commits']} commit")
        facts.append(f"• **GitHub:** terhubung ({', '.join(bits)}).")
    else:
        facts.append("• **GitHub:** belum terhubung.")
    facts.append("• **CV:** sudah diunggah." if cv else "• **CV:** belum diunggah.")

    role_text = f" untuk bidang **{role}**" if role else ""

    # Intent eksplisit dicek DULUAN, baru tebakan dari kata kunci. Kalau
    # urutannya dibalik, pertanyaan "rekomendasi lowongan magang" ikut
    # tertangkap cabang `career_path` karena mengandung kata "magang", dan
    # user tidak pernah sampai ke daftar lowongan yang dia minta.
    if intent == "find_internship":
        return _internship_answer(ctx, role)

    if intent == "explain_roadmap":
        if not ctx["roadmap_title"]:
            return "Belum ada roadmap yang terhubung ke akunmu. Selesaikan onboarding dulu."
        return (
            f"Pada roadmap **{ctx['roadmap_title']}**, progres belajarmu {rm_completed}/{rm_total} ({rm_pct}%).\n\n"
            "Fokuskan pada pemahaman konsep dasar dan selesaikan submission di setiap node "
            "untuk memperdalam penguasaan teknologi."
        )

    if intent == "career_path":
        # Tidak ada klaim "Job-ready". Readiness resmi dihitung di halaman
        # Career dari komponen yang sama persis, dan di sana bisa ditelusuri.
        return (
            f"Halo {name}! Ini data skema*{role_text} yang tercatat di akunmu:\n\n"
            + "\n".join(facts)
            + "\n\nSkor kesiapan karier dihitung dari komponen-komponen di atas dan "
            "ditampilkan lengkap di halaman **Career**, jadi angkanya bisa kamu periksa "
            "satu per satu.\n\n"
            + (
                "**Langkah berikutnya:** selesaikan roadmap materi inti dan buat project nyata."
                if rm_pct < 60
                else "Progres roadmap sudah decent. Fokuskan ke portofolio dan CV supaya lamaranmu lebih kuat."
            )
        )

    # Intent tidak dikenali: tebak dari kata kunci.
    if any(w in q for w in ["lowongan", "magang", "perusahaan", "rekrut"]):
        return _internship_answer(ctx, role)

    if any(w in q for w in ["roadmap", "materi", "belajar", "skill"]):
        if not ctx["roadmap_title"]:
            return "Belum ada roadmap yang terhubung ke akunmu. Selesaikan onboarding dulu."
        return (
            f"Pada roadmap **{ctx['roadmap_title']}**, progres belajarmu {rm_completed}/{rm_total} ({rm_pct}%).\n\n"
            "Fokuskan pada pemahaman konsep dasar dan selesaikan submission di setiap node "
            "untuk memperdalam penguasaan teknologi."
        )

    if any(w in q for w in ["siap", "ready", "karir", "career"]):
        return (
            f"Halo {name}! Ini data skema*{role_text} yang tercatat di akunmu:\n\n"
            + "\n".join(facts)
            + "\n\nSkor kesiapan karier dihitung dari komponen-komponen di atas dan "
            "ditampilkan lengkap di halaman **Career**, jadi angkanya bisa kamu periksa "
            "satu per satu."
        )

    return (
        f"Halo {name}! Saya bisa bantu soal roadmap, kesiapan karier, dan lowongan magang{role_text}.\n\n"
        + "\n".join(facts)
    )


def _internship_answer(ctx: dict, role: Optional[str]) -> str:
    """Jawaban rekomendasi lowongan, hanya dari yang benar-benar cocok."""
    if not role:
        return (
            "Lowongan magang dicocokkan dari role hasil onboarding kamu, dan role itu "
            "belum tercatat. Selesaikan onboarding dulu supaya kami bisa mencocokkannya."
        )

    if not ctx["internships"]:
        return (
            f"Tidak ada lowongan di katalog yang tech stack-nya cocok dengan role **{role}**. "
            "Kontak perusahaan yang tersedia ada di halaman **Career**."
        )

    lines = []
    for item in ctx["internships"]:
        skills = (
            " — tech stack yang sama: " + ", ".join(item["matched_skills"])
            if item["matched_skills"]
            else ""
        )
        lines.append(
            f"• **{item['company']}** — {item['role']} ({item['location']}), "
            f"cocok {item['match']}%{skills}"
        )
    return (
        f"Lowongan yang tech stack-nya paling dekat dengan role **{role}** kamu:\n\n"
        + "\n".join(lines)
        + "\n\nPersentase dihitung dari banyaknya tech stack role kamu yang sama dengan "
        "tag lowongannya, jadi urutannya bisa berbeda antarrole."
    )


async def call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    api_key = (
        getattr(settings, "OPENAI_API_KEY", None)
        or os.environ.get("OPENAI_API_KEY")
        or getattr(settings, "GEMINI_API_KEY", None)
        or os.environ.get("GEMINI_API_KEY")
    )
    if not api_key:
        return None

    try:
        from openai import OpenAI
        base_url = None
        if "AIzaSy" in api_key:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        client = OpenAI(api_key=api_key, base_url=base_url)
        model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini") if not base_url else "gemini-2.0-flash"
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )
        return res.choices[0].message.content
    except Exception:
        return None


async def assist(
    db: AsyncSession,
    req: AiAssistRequest,
    user_id: Optional[uuid.UUID] = None,
) -> AiAssistResponse:
    ctx = await _gather_user_context(db, user_id)

    gh_line = "Belum terhubung"
    if ctx["github_stats"]:
        parts = [f"{ctx['github_stats']['repos']} repo publik"]
        if ctx["github_stats"]["commits"] is not None:
            parts.insert(0, f"{ctx['github_stats']['commits']} commit")
        gh_line = "Terhubung (" + ", ".join(parts) + ")"

    system_prompt = (
        "Kamu adalah Sepaham Career & Learning AI, mentor teknologi berpengalaman yang ramah, "
        "praktis, dan terarah untuk mahasiswa IT di Indonesia.\n"
        "Pakai HANYA data di bawah. Jangan mengarang angka, skor, atau fakta lain. "
        "Kalau ada yang tidak diketahui, katakan belum diketahui.\n"
        f"Data pengguna saat ini:\n"
        f"- Nama: {ctx['user_name']}\n"
        f"- Role Minat: {ctx['role_title'] or 'belum ditentukan'}\n"
        f"- Roadmap: {ctx['roadmap_title'] or 'belum ada'} "
        f"(Progres: {ctx['roadmap_completed']}/{ctx['roadmap_total']} node)\n"
        f"- GitHub: {gh_line}\n"
        f"- CV: {'Sudah diunggah' if ctx['cv_uploaded'] else 'Belum diunggah'}\n"
        f"- Lowongan magang yang cocok: "
        + (
            "; ".join(
                f"{item['company']} — {item['role']} (cocok {item['match']}%)"
                for item in ctx["internships"]
            )
            if ctx["internships"]
            else "belum ada yang bisa dicocokkan"
        )
        + "\n\n"
        f"Intent pertanyaan: {req.intent}.\n"
        "Berikan jawaban yang memotivasi, langsung menjawab pertanyaan, berbasis data kemajuan user di atas, dengan format markdown yang rapi."
    )

    llm_resp = await call_llm(system_prompt, req.message)
    if llm_resp:
        return AiAssistResponse(response=llm_resp, source="llm")

    fallback = _generate_rule_based_fallback(req.message, req.intent or "general", ctx)
    return AiAssistResponse(response=fallback, source="rule_based")


async def generate(
    db: AsyncSession,
    req: AiGenerateRequest,
    user_id: Optional[uuid.UUID] = None,
) -> AiGenerateResponse:
    ctx = await _gather_user_context(db, user_id)
    system_prompt = (
        "Kamu adalah asisten AI Sepaham yang memiliki wawasan penuh tentang platform pembelajaran IT Sepaham. "
        "Bantu pengguna menjawab pertanyaan mereka dengan jelas, akurat, dan mendalam."
    )
    llm_resp = await call_llm(system_prompt, req.message)
    if llm_resp:
        return AiGenerateResponse(response=llm_resp, source="llm")

    fallback = _generate_rule_based_fallback(req.message, "general", ctx)
    return AiGenerateResponse(response=fallback, source="rule_based")
