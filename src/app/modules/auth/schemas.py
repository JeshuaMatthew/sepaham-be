from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

# Panjang minimum password. 6 karakter terlalu pendek untuk dipakai di mana
# pun. Ini bukan pengukuran keamanan, tapi tidak ada alasan membiarkannya.
MIN_PASSWORD_LENGTH = 8

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    # `role` sengaja tidak ada di sini. Sebelumnya klien boleh mengirim
    # `role: "faculty"` dan endpoint registrasi membuat akun dosen untuk siapa
    # saja yang mengirimnya. Akun faculty hanya dibuat lewat provisioning,
    # bukan lewat API publik.

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email tidak valid")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password minimal {MIN_PASSWORD_LENGTH} karakter")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama tidak boleh kosong")
        return v

class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()

class UserDetail(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_new_user: bool = Field(default=False, serialization_alias="isNewUser", validation_alias="isNewUser")

    model_config = ConfigDict(populate_by_name=True)

class AuthResponse(BaseModel):
    token: str
    user: UserDetail

class GoogleAuthRequest(BaseModel):
    """Kredensial hasil login Google.

    Hanya dua field, keduanya kredensial asli dari Google:
    - `credential`  : ID token (JWT) dari Google Identity Services
    - `access_token`: OAuth access token dari popup Google

    `email` dan `name` TIDAK diterima. Sebelumnya keduanya ada di sini dan
    dipakai kalau verifikasi gagal, sehingga `POST /api/auth/google` dengan
    body `{"email": "kositasi@..."}` saja berhasil memberi token untuk akun
    mana saja. Sekarang kalau tidak ada kredensial yang bisa diverifikasi,
    jawabannya 401.
    """

    credential: Optional[str] = None
    access_token: Optional[str] = None
