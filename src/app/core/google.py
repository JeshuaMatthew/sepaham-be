"""
Verifikasi identitas Google.

Dua jalur, keduanya diverifikasi oleh Google:

1. `verify_id_token(credential)` — ID token (JWT) dari Google's JS library.
   Signature dicek terhadap JWKS Google, lalu `iss`, `aud`, dan `exp` diperiksa.
2. `verify_access_token(access_token)` — OAuth access token dari popup.
   Ditukar ke endpoint `userinfo` Google; kalau token salah, Google yang
   menolak sehingga kita tidak perlu menebak-nebak.

Yang TIDAK ada di sini: membaca `email` dari body request. Kalau sebuah payload
tidak bisa diverifikasi, jawabannya 401. Dulu alur ini menerima `email` mentah
dari klien sehingga siapa pun bisa login sebagai akun mana saja.
"""

import httpx
import jwt
from fastapi import HTTPException, status

from src.app.core.config import settings
from src.app.core.logger import app_logger

# Google menandatangani ID token dengan RSA dan menerbitkan JWKS di sini.
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_ISSUERS = frozenset(
    {
        "https://accounts.google.com",
        "accounts.google.com",
    }
)

# Cache JWKS di proses supaya tidak fetch ulang tiap login. Kunci Google's
# hanya berganti saat mereka rotasi, jadi cache ini cukup.
_jwk_client = jwt.PyJWKClient(GOOGLE_JWKS_URL)


class GoogleVerificationError(Exception):
    """Kredensial Google tidak bisa diverifikasi."""


def verify_id_token(credential: str) -> tuple[str, str]:
    """Verifikasi ID token Google. Return (email, name).

    Raises `GoogleVerificationError` kalau signature, issuer, audience, atau
    masa berlaku tidak cocok.
    """
    if not settings.GOOGLE_CLIENT_ID:
        # Tanpa client id kita tidak bisa memeriksa `aud`, jadi jangan
        # menerima ID token yang mungkin milik aplikasi lain.
        raise GoogleVerificationError("GOOGLE_CLIENT_ID belum dikonfigurasi")

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(credential)
        payload = jwt.decode(
            credential,
            key=signing_key.key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            issuer=list(GOOGLE_ISSUERS),
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except GoogleVerificationError:
        raise
    except Exception as exc:  # PyJWT melempar banyak tipe error berbeda
        raise GoogleVerificationError(f"ID token tidak valid: {exc}") from exc

    email = payload.get("email")
    # Google hanya menandai email terverifikasi kalau user menyetujui.
    if not email or payload.get("email_verified") not in (True, "true"):
        raise GoogleVerificationError("Email Google tidak terverifikasi")

    return str(email), str(payload.get("name") or "")


async def verify_access_token(access_token: str) -> tuple[str, str]:
    """Verifikasi OAuth access token lewat endpoint userinfo Google.

    Return (email, name). Raises `GoogleVerificationError` kalau Google menolak
    tokennya atau tidak mengembalikan email.
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
    except Exception as exc:
        raise GoogleVerificationError(f"Gagal menghubungi Google: {exc}") from exc

    if res.status_code != 200:
        raise GoogleVerificationError(f"Access token ditolak Google (HTTP {res.status_code})")

    info = res.json()
    email = info.get("email")
    if not email or info.get("verified_email") is not True:
        raise GoogleVerificationError("Email Google tidak terverifikasi")

    return str(email), str(info.get("name") or "")


async def verify_google_credentials(credential: str | None, access_token: str | None) -> tuple[str, str]:
    """Coba ID token dulu, lalu access token. Salah satu harus valid."""
    if credential:
        try:
            return verify_id_token(credential)
        except GoogleVerificationError as exc:
            app_logger.warning("ID token Google ditolak: %s", exc)

    if access_token:
        try:
            return await verify_access_token(access_token)
        except GoogleVerificationError as exc:
            app_logger.warning("Access token Google ditolak: %s", exc)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kredensial Google tidak valid atau kedaluwarsa.",
    )
