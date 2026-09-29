import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.app.core.logger import app_logger
from src.app.modules.profile.entity import Profile
from src.app.modules.github.entity import GithubStats, GithubRepo
from src.app.modules.github.schemas import (
    GithubCardResponse,
    GithubStatsObj,
    TopLanguageItem,
    TopRepoItem,
    GithubConnectRequest,
)

LANGUAGE_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Java": "#b07219",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Shell": "#89e051",
    "Vue": "#41b883",
    "Elixir": "#6e4a7e",
    "PHP": "#4F5D95",
    "Scala": "#c22d40",
    "Haskell": "#5e5086",
    "Lua": "#000080",
}

UNKNOWN_LANGUAGE_COLOR = "#8b949e"

# Pola username GitHub.
_USERNAME_RE = r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$"


async def get_github_card(db: AsyncSession, user_id: uuid.UUID) -> GithubCardResponse:
    stats_res = await db.execute(select(GithubStats).where(GithubStats.user_id == user_id))
    stats = stats_res.scalar_one_or_none()
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub belum dihubungkan",
        )

    repos_res = await db.execute(
        select(GithubRepo).where(GithubRepo.user_id == user_id).order_by(GithubRepo.stars.desc())
    )
    repos = repos_res.scalars().all()

    return GithubCardResponse(
        username=stats.username,
        stats=GithubStatsObj(
            # Kolom ini nullable karena GitHub tidak-provider public API-nya
            # tanpa token. `null` berarti "tidak diketahui", bukan nol.
            total_commits=stats.total_commits,
            current_streak=stats.current_streak,
            longest_streak=stats.longest_streak,
            public_repos=stats.public_repos or 0,
        ),
        topLanguages=[
            TopLanguageItem(name=item["name"], percentage=item["percentage"], color=item["color"])
            for item in (stats.top_languages or [])
        ],
        weeks=stats.weeks or [],
        topRepos=[
            TopRepoItem(
                id=str(repo.id),
                name=repo.name,
                description=repo.description or "",
                stars=repo.stars,
                forks=repo.forks,
                language=repo.language or "",
                languageColor=repo.language_color or "",
                url=repo.url or "",
            )
            for repo in repos
        ],
    )


class GithubFetchError(Exception):
    """Data GitHub tidak bisa diambil.

    Dilempar ke pemanggil supaya `connect_github` membalas error, bukan
    menyimpan angka karangan. Ini yang terjadi sebelum: fetch gagal diam-diam
    lalu user dapat `28 repos / 1245 commits / streak 17` yang tidak bisa
    dibedakan dari hasil pengambilan yang sukses.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


async def fetch_real_github_data(username: str) -> dict:
    """Ambil data publik GitHub satu user.

    Yang bisa diambil tanpa token hanya `public_repos`, bahasa dari daftar
    repo, dan repo itu sendiri. Jumlah commit, streak harian, dan grafik
    kontribusi TIDAK tersedia di API publik GitHub, jadi tidak dikarang di
    sini: kolomnya dibiarkan null.
    """
    import httpx

    headers = {"User-Agent": "Sepaham-App", "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
        user_res = await client.get(f"https://api.github.com/users/{username}")
        if user_res.status_code == 404:
            raise GithubFetchError(f"Username GitHub '{username}' tidak ditemukan.")
        if user_res.status_code == 403:
            raise GithubFetchError("GitHub membalas 403 (rate limit). Coba lagi nanti.")
        if user_res.status_code != 200:
            raise GithubFetchError(f"GitHub membalas HTTP {user_res.status_code}.")

        user_data = user_res.json()
        public_repos = int(user_data.get("public_repos") or 0)

        repos_res = await client.get(
            f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
        )
        if repos_res.status_code != 200 or not isinstance(repos_res.json(), list):
            raise GithubFetchError("Gagal mengambil daftar repository GitHub.")
        repos_data = repos_res.json()

    # Bahasa dihitung dari JUMLAH repo per bahasa, bukan ukuran byte. Ini
    # perkiraan kasar, tapi kalau diberi label "share of repositories" di UI
    # maka tidak menyesatkan.
    lang_counts: dict[str, int] = {}
    for repo in repos_data:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    total_repos_with_lang = sum(lang_counts.values())
    top_languages = []
    if total_repos_with_lang:
        for lang, count in sorted(lang_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]:
            top_languages.append(
                {
                    "name": lang,
                    "percentage": round((count / total_repos_with_lang) * 100),
                    "color": LANGUAGE_COLORS.get(lang, UNKNOWN_LANGUAGE_COLOR),
                }
            )

    top_repos = [
        {
            "name": repo.get("name", ""),
            "description": repo.get("description") or "",
            "stars": int(repo.get("stargazers_count") or 0),
            "forks": int(repo.get("forks_count") or 0),
            "language": repo.get("language") or "",
            "language_color": LANGUAGE_COLORS.get(repo.get("language") or "", UNKNOWN_LANGUAGE_COLOR),
            "url": repo.get("html_url") or f"https://github.com/{username}/{repo.get('name', '')}",
        }
        for repo in repos_data[:6]
    ]

    return {
        "public_repos": public_repos,
        "top_languages": top_languages,
        "top_repos": top_repos,
    }


def _validate_username(username: str) -> str:
    value = (username or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username GitHub wajib diisi",
        )
    if not re.match(_USERNAME_RE, value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format username GitHub tidak valid",
        )
    return value


async def connect_github(
    db: AsyncSession, user_id: uuid.UUID, req: GithubConnectRequest
) -> GithubCardResponse:
    """Tautkan username GitHub dan simpan data publiknya.

    Catatan penting soal batas endpoint ini: tidak ada alur OAuth, jadi
    server tidak punya bukti bahwa username itu milik pengguna yang sedang
    login. Anyone yang menebak username orang lain bisa melihat repo publik
    mereka. Itu memang data publik, tapi untuk mientras tombol connect
    tidak ditampilkan di UI, jadi endpoint ini belum dipakai.
    """
    username = _validate_username(req.username)

    try:
        data = await fetch_real_github_data(username)
    except GithubFetchError as exc:
        # Gagal ambil = gagal. Jangan menyimpan apa pun dan jangan mengarang
        # pengganti, karena UI tidak bisa membedakan data karangan dari nyata.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        app_logger.error("Gagal menghubungi GitHub API: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Tidak bisa menghubungi GitHub. Coba lagi nanti.",
        ) from exc

    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
    profile.github_connected = True
    profile.github_username = username

    # `total_commits`, `current_streak`, `longest_streak`, dan `weeks` sengaja
    # `None`. API publik GitHub tidak menyediakan angka-angka itu tanpa token,
    # dan mengarangnya lebih buruk daripada tidak menampilkannya.
    stmt = insert(GithubStats).values(
        user_id=user_id,
        username=username,
        total_commits=None,
        current_streak=None,
        longest_streak=None,
        public_repos=data["public_repos"],
        top_languages=data["top_languages"],
        weeks=None,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        # Semua kolom ikut ditulis. `set_` yang tidak menyertakan kolom streak
        # membuat nilai lama bertahan setelah connect ulang.
        set_={
            "username": username,
            "total_commits": None,
            "current_streak": None,
            "longest_streak": None,
            "public_repos": data["public_repos"],
            "top_languages": data["top_languages"],
            "weeks": None,
        },
    )
    await db.execute(stmt)

    await db.execute(delete(GithubRepo).where(GithubRepo.user_id == user_id))
    for repo in data["top_repos"]:
        db.add(
            GithubRepo(
                user_id=user_id,
                name=repo["name"],
                description=repo["description"],
                stars=repo["stars"],
                forks=repo["forks"],
                language=repo["language"],
                language_color=repo["language_color"],
                url=repo["url"],
            )
        )

    await db.commit()

    return await get_github_card(db, user_id)


async def disconnect_github(db: AsyncSession, user_id: uuid.UUID) -> None:
    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        profile.github_connected = False
        profile.github_username = None

    await db.execute(delete(GithubStats).where(GithubStats.user_id == user_id))
    await db.execute(delete(GithubRepo).where(GithubRepo.user_id == user_id))
    await db.commit()
