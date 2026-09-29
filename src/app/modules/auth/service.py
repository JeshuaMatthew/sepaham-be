import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.core.security import hash_password, verify_password, create_access_token
from src.app.core.enums import UserRole
from src.app.core.google import verify_google_credentials
from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    GoogleAuthRequest,
    AuthResponse,
    UserDetail,
)

async def register(db: AsyncSession, req: RegisterRequest) -> AuthResponse:
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar",
        )

    pwd_hash = hash_password(req.password)
    # Role hardcoded. `RegisterRequest` tidak punya field `role` karena klien
    # pernah memakainya untuk mendaftar sebagai faculty.
    new_user = User(
        email=req.email,
        password_hash=pwd_hash,
        role=UserRole.STUDENT.value,
        name=req.name,
    )
    db.add(new_user)
    await db.flush()

    new_profile = Profile(user_id=new_user.id)
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_user)

    role_str = new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role)
    token = create_access_token(user_id=str(new_user.id), role=role_str)

    return AuthResponse(
        token=token,
        user=UserDetail(
            id=str(new_user.id),
            email=new_user.email,
            name=new_user.name,
            role=role_str,
            isNewUser=True,
        ),
    )

async def login(db: AsyncSession, req: LoginRequest) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email tidak ditemukan atau password salah",
        )

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(user_id=str(user.id), role=role_str)

    return AuthResponse(
        token=token,
        user=UserDetail(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=role_str,
            isNewUser=False,
        ),
    )

async def get_me(db: AsyncSession, user_id: uuid.UUID) -> UserDetail:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan",
        )

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    return UserDetail(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=role_str,
        isNewUser=False,
    )

async def google_auth(db: AsyncSession, req: GoogleAuthRequest) -> AuthResponse:
    """
    Login lewat Google.

    Email dan nama SELALU berasal dari kredensial Google yang sudah
    diverifikasi. Alur lama jatuh ke `req.email` dari body kalau decode JWT
    gagal, sehingga `POST /api/auth/google {"email": "..."}` tanpa Google
    sama sekali berhasil membuat token. Sekarang `verify_google_credentials`
    melempar 401 kalau tidak ada kredensial yang sah.
    """
    email, name = await verify_google_credentials(req.credential, req.access_token)

    email = email.strip().lower()
    if not name:
        name = email.split("@")[0] or "Google User"

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    is_new = False

    if not user:
        is_new = True
        pwd_hash = hash_password(uuid.uuid4().hex)
        user = User(
            email=email,
            password_hash=pwd_hash,
            # Akun baru dari Google selalu student, sama seperti registrasi
            # biasa. Faculty dibuat lewat provisioning.
            role=UserRole.STUDENT.value,
            name=name,
        )
        db.add(user)
        await db.flush()

        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(user)

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(user_id=str(user.id), role=role_str)

    return AuthResponse(
        token=token,
        user=UserDetail(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=role_str,
            isNewUser=is_new,
        ),
    )
