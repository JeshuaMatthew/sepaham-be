import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import text as sa_text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.modules.community.entity import Server
from src.app.modules.community.schemas import ServerObj
from src.app.modules.collab.entity import CollabRequest
from src.app.modules.collab import service as collab_service
from src.app.modules.faculty.schemas import (
    FacultyStudentsResponse,
    FacultyStudentItem,
    StudentRoadmap,
    StudentGithub,
    FacultyServersResponse,
    BanServerResponse,
    FacultyRequestsResponse,
    CloseCollabRequestResponse,
    RoleResponse,
    RoleUpsertRequest,
)

async def get_students(db: AsyncSession) -> FacultyStudentsResponse:
    query = sa_text("""
        SELECT
            u.id::text AS id,
            u.name,
            COALESCE(p.avatar_url, '') AS avatar,
            COALESCE(p.role_title, '') AS role,
            p.cv_file_name,
            to_char(p.cv_uploaded_at, 'YYYY-MM-DD') AS cv_uploaded_at,
            COALESCE(rm.title, '') AS roadmap_title,
            COALESCE((SELECT count(*) FROM roadmap_nodes n WHERE n.roadmap_id = rm.id), 0) AS roadmap_total,
            COALESCE((SELECT count(*) FROM submissions s
                      WHERE s.user_id = u.id AND s.roadmap_id = rm.id AND s.done), 0) AS roadmap_completed,
            COALESCE(gs.public_repos, 0) AS gh_repos,
            gs.total_commits AS gh_commits,
            COALESCE(
                (SELECT array_agg(elem->>'name') FROM jsonb_array_elements(gs.top_languages) elem),
                ARRAY[]::text[]
            ) AS gh_langs,
            (SELECT count(*) FROM collab_requests c WHERE c.author_id = u.id) AS projects
        FROM users u
        LEFT JOIN profiles p ON p.user_id = u.id
        LEFT JOIN user_preferences pref ON pref.user_id = u.id
        LEFT JOIN roadmaps rm ON rm.role_id = pref.role_id
        LEFT JOIN github_stats gs ON gs.user_id = u.id
        WHERE u.role = 'student'
        ORDER BY u.created_at;
    """)
    result = await db.execute(query)
    rows = result.fetchall()

    students = []
    for r in rows:
        students.append(
            FacultyStudentItem(
                id=str(r.id),
                name=r.name,
                avatar=r.avatar,
                role=r.role,
                cv_file_name=r.cv_file_name,
                cv_uploaded_at=r.cv_uploaded_at,
                roadmap=StudentRoadmap(
                    title=r.roadmap_title,
                    completed=r.roadmap_completed,
                    total=r.roadmap_total,
                ),
                github=StudentGithub(
                    repos=r.gh_repos,
                    commits=r.gh_commits,
                    top_languages=list(r.gh_langs) if r.gh_langs else [],
                ),
                projects=r.projects,
            )
        )

    return FacultyStudentsResponse(students=students)

async def get_servers(db: AsyncSession) -> FacultyServersResponse:
    stmt = select(Server).order_by(Server.created_at)
    result = await db.execute(stmt)
    servers = result.scalars().all()

    server_objs = [
        ServerObj(
            id=s.id,
            name=s.name,
            initial=s.initial,
            color=s.color,
        )
        for s in servers
        if not s.banned
    ]
    banned_ids = [s.id for s in servers if s.banned]

    return FacultyServersResponse(servers=server_objs, banned_ids=banned_ids)

async def ban_server(db: AsyncSession, faculty_id: uuid.UUID, server_id: str) -> BanServerResponse:
    stmt = select(Server).where(Server.id == server_id)
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server tidak ditemukan",
        )

    server.banned = not server.banned
    server.banned_by = faculty_id if server.banned else None
    server.banned_at = datetime.now(timezone.utc) if server.banned else None
    await db.commit()

    return BanServerResponse(id=server.id, banned=server.banned)

async def get_requests(db: AsyncSession) -> FacultyRequestsResponse:
    all_requests = await collab_service.get_requests(db, include_closed=True)
    
    stmt = select(CollabRequest.id).where(CollabRequest.closed.is_(True))
    result = await db.execute(stmt)
    closed_ids = [str(uid) for uid in result.scalars().all()]

    return FacultyRequestsResponse(requests=all_requests.requests, closed_ids=closed_ids)

async def close_request(db: AsyncSession, request_id: uuid.UUID) -> CloseCollabRequestResponse:
    stmt = select(CollabRequest).where(CollabRequest.id == request_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collab request tidak ditemukan",
        )

    req.closed = not req.closed
    req.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return CloseCollabRequestResponse(id=str(req.id), closed=req.closed)


# ===== Role Management =====

async def list_roles(db: AsyncSession) -> list[RoleResponse]:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).order_by(Role.sort_order)
    result = await db.execute(stmt)
    roles = result.scalars().all()

    return [
        RoleResponse(
            id=r.id,
            title=r.title,
            emoji=r.emoji or "",
            tagline=r.tagline or "",
            description=r.description or "",
            accent=r.accent or "",
        )
        for r in roles
    ]


async def create_role(db: AsyncSession, req: RoleUpsertRequest) -> RoleResponse:
    from src.app.modules.catalog.entity import Role

    role = Role(
        id=req.title.lower().replace(" ", "-").replace("/", "-"),
        title=req.title,
        emoji=req.emoji or "",
        tagline=req.tagline or "",
        description=req.description or "",
        accent=req.accent or "",
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        title=role.title,
        emoji=role.emoji or "",
        tagline=role.tagline or "",
        description=role.description or "",
        accent=role.accent or "",
    )


async def update_role(db: AsyncSession, role_id: str, req: RoleUpsertRequest) -> RoleResponse:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role tidak ditemukan",
        )

    role.title = req.title
    role.emoji = req.emoji or ""
    role.tagline = req.tagline or ""
    role.description = req.description or ""
    role.accent = req.accent or ""
    await db.commit()
    await db.refresh(role)

    return RoleResponse(
        id=role.id,
        title=role.title,
        emoji=role.emoji or "",
        tagline=role.tagline or "",
        description=role.description or "",
        accent=role.accent or "",
    )


async def delete_role(db: AsyncSession, role_id: str) -> None:
    from src.app.modules.catalog.entity import Role

    stmt = select(Role).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role tidak ditemukan",
        )

    await db.delete(role)
    await db.commit()


# ===== Student CV =====

CV_UPLOAD_DIR = Path("uploads")
CV_ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx"})
CV_MIME_BY_EXT = {".pdf": "application/pdf", ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


async def get_student_cv(db: AsyncSession, student_id: uuid.UUID) -> FileResponse:
    """Kembalikan berkas CV mahasiswa untuk diunduh dosen.

    Sebelumnya modal "View CV" di frontend hanya menampilkan placeholder
    "isn't available in this demo" — tombolnya ada tapi tidak melakukan
    apa-apa. Sekarang berkas asli yang diunggah mahasiswa dikembalikan.
    """
    from src.app.modules.profile.entity import Profile

    res = await db.execute(select(Profile).where(Profile.user_id == student_id))
    profile = res.scalar_one_or_none()
    if profile is None or not profile.cv_file_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mahasiswa ini belum mengunggah CV",
        )

    filename = profile.cv_file_name.split("/")[-1].split("?")[0]
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV tidak ditemukan",
        )

    path = CV_UPLOAD_DIR / filename
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Berkas CV tidak ditemukan di server",
        )

    ext = Path(filename).suffix.lower()
    media_type = CV_MIME_BY_EXT.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
    )

