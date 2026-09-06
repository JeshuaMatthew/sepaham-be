from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from src.app.core.config import settings

_ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash password using Argon2 with a random salt."""
    return _ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against an Argon2 hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False

def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate HS256 JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate HS256 JWT access token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
