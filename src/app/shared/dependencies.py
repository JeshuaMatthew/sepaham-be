from typing import Annotated, Optional
import uuid
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from src.app.core.database import get_db
from src.app.core.security import decode_access_token
from src.app.modules.auth.entity import User

class AuthUser:
    def __init__(self, user_id: uuid.UUID, email: str, role: str, name: str):
        self.id = user_id
        self.email = email
        self.role = role
        self.name = name

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header otorisasi diperlukan",
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format token tidak valid. Gunakan 'Bearer <token>'",
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token telah kedaluwarsa",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Klaim token tidak lengkap",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID pada token tidak valid",
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan",
        )

    return AuthUser(
        user_id=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        name=user.name,
    )

async def get_current_faculty(
    current_user: Annotated[AuthUser, Depends(get_current_user)]
) -> AuthUser:
    if current_user.role != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses khusus untuk akun Dosen (Faculty)",
        )
    return current_user

CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
FacultyUser = Annotated[AuthUser, Depends(get_current_faculty)]
