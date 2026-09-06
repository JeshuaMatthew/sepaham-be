import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from src.app.modules.profile.entity import Profile
from src.app.modules.github.entity import GithubStats, GithubRepo
from src.app.modules.github.schemas import (
    GithubCardResponse,
    GithubStatsObj,
    TopLanguageItem,
    TopRepoItem,
    GithubConnectRequest,
)

DEMO_TOP_LANGUAGES = [
    {"name": "TypeScript", "percentage": 42, "color": "#3987e5"},
    {"name": "Python", "percentage": 30, "color": "#3572A5"},
    {"name": "Rust", "percentage": 18, "color": "#dea584"},
    {"name": "Go", "percentage": 10, "color": "#00ADD8"},
]

DEMO_WEEKS = [
    [0, 2, 4, 1, 0, 0, 0],
    [1, 3, 5, 2, 4, 0, 0],
    [0, 0, 6, 8, 3, 2, 1],
    [2, 4, 1, 0, 5, 3, 0],
    [0, 11, 9, 6, 0, 0, 0],
    [3, 5, 2, 7, 4, 1, 0],
    [0, 2, 4, 1, 0, 0, 0],
    [1, 3, 5, 2, 4, 0, 0],
    [0, 0, 6, 8, 3, 2, 1],
    [2, 4, 1, 0, 5, 3, 0],
    [0, 11, 9, 6, 0, 0, 0],
    [3, 5, 2, 7, 4, 1, 0],
    [0, 2, 4, 1, 0, 0, 0],
    [1, 3, 5, 2, 4, 0, 0],
    [0, 0, 6, 8, 3, 2, 1],
    [2, 4, 1, 0, 5, 3, 0],
]

DEMO_REPOS = [
    {
        "name": "sepaham-fe",
        "description": "Frontend for the Sepaham platform",
        "stars": 128,
        "forks": 18,
        "language": "TypeScript",
        "language_color": "#3987e5",
        "url": "https://github.com/budisantoso/sepaham-fe",
    },
    {
        "name": "fastapi-microservices",
        "description": "High performance async microservices template",
        "stars": 85,
        "forks": 12,
        "language": "Python",
        "language_color": "#3572A5",
        "url": "https://github.com/budisantoso/fastapi-microservices",
    },
    {
        "name": "ai-code-analyzer",
        "description": "AI-powered static code analysis tool",
        "stars": 64,
        "forks": 9,
        "language": "Rust",
        "language_color": "#dea584",
        "url": "https://github.com/budisantoso/ai-code-analyzer",
    },
]

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
            totalCommits=stats.total_commits,
            currentStreak=stats.current_streak,
            longestStreak=stats.longest_streak,
            publicRepos=stats.public_repos,
        ),
        topLanguages=[
            TopLanguageItem(name=l["name"], percentage=l["percentage"], color=l["color"])
            for l in (stats.top_languages or [])
        ],
        weeks=stats.weeks or [],
        topRepos=[
            TopRepoItem(
                id=str(r.id),
                name=r.name,
                description=r.description or "",
                stars=r.stars,
                forks=r.forks,
                language=r.language or "",
                languageColor=r.language_color or "",
                url=r.url or "",
            )
            for r in repos
        ],
    )

async def connect_github(
    db: AsyncSession, user_id: uuid.UUID, req: GithubConnectRequest
) -> GithubCardResponse:
    username = (req.username or "yourhandle").strip()

    # 1. Update Profile
    prof_res = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    profile.github_connected = True
    profile.github_username = username

    # 2. Upsert GithubStats
    stmt = insert(GithubStats).values(
        user_id=user_id,
        username=username,
        total_commits=1245,
        current_streak=17,
        longest_streak=63,
        public_repos=28,
        top_languages=DEMO_TOP_LANGUAGES,
        weeks=DEMO_WEEKS,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "username": username,
            "top_languages": DEMO_TOP_LANGUAGES,
            "weeks": DEMO_WEEKS,
        },
    )
    await db.execute(stmt)

    # 3. Replace Repos
    await db.execute(delete(GithubRepo).where(GithubRepo.user_id == user_id))
    for r in DEMO_REPOS:
        db.add(
            GithubRepo(
                user_id=user_id,
                name=r["name"],
                description=r["description"],
                stars=r["stars"],
                forks=r["forks"],
                language=r["language"],
                language_color=r["language_color"],
                url=r["url"],
            )
        )

    await db.commit()

    return await get_github_card(db, user_id)
