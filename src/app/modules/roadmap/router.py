from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.database import get_db
from src.app.shared.dependencies import CurrentUser, FacultyUser
from src.app.shared.Services.storage import save_uploaded_file
from src.app.modules.roadmap import service
from src.app.modules.roadmap.schemas import (
    RoadmapsListResponse,
    RoadmapDetailResponse,
    RoadmapUpsertRequest,
    SubmissionState,
    SubmissionUpsertRequest,
    UploadedFileResponse,
)

router = APIRouter(prefix="/api", tags=["Roadmap"])

@router.get("/roadmaps", response_model=RoadmapsListResponse, status_code=status.HTTP_200_OK)
async def get_roadmaps(db: AsyncSession = Depends(get_db)):
    return await service.get_roadmaps(db)

@router.get("/roadmaps/{id}", response_model=RoadmapDetailResponse, status_code=status.HTTP_200_OK)
async def get_roadmap_detail(id: str, db: AsyncSession = Depends(get_db)):
    return await service.get_roadmap_detail(db, id)

@router.put("/roadmaps/{id}", status_code=status.HTTP_200_OK)
async def upsert_roadmap(
    id: str,
    req: RoadmapUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.upsert_roadmap(db, id, req, faculty.id)

@router.post("/roadmaps", status_code=status.HTTP_201_CREATED)
async def create_roadmap(
    req: RoadmapUpsertRequest,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Buat roadmap baru. Id dibuat server, bukan `custom-xxx` dari browser."""
    return await service.create_roadmap(db, req, faculty.id)

@router.delete("/roadmaps/{id}", status_code=status.HTTP_200_OK)
async def delete_roadmap(
    id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.delete_roadmap(db, id)

@router.get("/roadmaps/{id}/submissions", response_model=dict[str, SubmissionState], status_code=status.HTTP_200_OK)
async def get_submissions(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_submissions(db, user.id, id)

@router.put("/roadmaps/{id}/nodes/{node_key}/submission", response_model=SubmissionState, status_code=status.HTTP_200_OK)
async def upsert_submission(
    id: str,
    node_key: str,
    req: SubmissionUpsertRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.upsert_submission(db, user.id, id, node_key, req)

@router.post(
    "/roadmaps/{id}/nodes/{node_key}/submission/file",
    response_model=UploadedFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_submission_file(
    id: str,
    node_key: str,
    user: CurrentUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Unggah bukti berkas untuk node bertipe `file`.

    Sebelumnya UI roadmap hanya membaca `File.name` lalu mengirimnya sebagai
    `fileName`, tanpa pernah mengunggah apa pun. Server lalu menandai node
    selesai hanya karena string nama berkas tidak kosong, jadi progres yang
    dilihat dosen bisa dibuat tanpa kirim berkas apa pun.
    """
    return await service.upload_submission_file(db, user.id, id, node_key, file)


@router.post("/roadmaps/{id}/activity", status_code=status.HTTP_200_OK)
async def record_activity(
    id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.record_activity(db, user.id, id)

@router.get(
    "/faculty/roadmaps/{id}",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_faculty_roadmap_detail(
    id: str,
    faculty: FacultyUser,
    db: AsyncSession = Depends(get_db),
):
    """Roadmap lengkap dengan kunci jawaban, khusus dosen.

    Endpoint mahasiswa membuang `correctIndex` supaya penilaian quiz tidak
    bisa dimanipulasi dari browser. Editor soal dosen justru membutuhkan
    kunci itu, jadi ada jalur terpisah yang butuh akun faculty.
    """
    return await service.get_roadmap_detail(db, id, include_answer_key=True)


@router.get("/roadmap-activity", response_model=dict[str, int], status_code=status.HTTP_200_OK)
async def get_user_activities(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user_activities(db, user.id)
