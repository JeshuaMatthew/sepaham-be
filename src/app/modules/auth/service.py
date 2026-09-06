import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.core.security import hash_password, verify_password, create_access_token
from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.auth.schemas import RegisterRequest, LoginRequest, AuthResponse, UserDetail

async def register(db: AsyncSession, req: RegisterRequest) -> AuthResponse:
    # 1. Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar",
        )

    # 2. Create user
    pwd_hash = hash_password(req.password)
    user_role_val = req.role.value if req.role else "student"
    new_user = User(
        email=req.email,
        password_hash=pwd_hash,
        role=user_role_val,
        name=req.name,
    )
    db.add(new_user)
    await db.flush()  # to get new_user.id

    # 3. Create empty profile in the same transaction
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
