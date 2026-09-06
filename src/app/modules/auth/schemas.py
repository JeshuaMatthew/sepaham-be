from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from src.app.core.enums import UserRole

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: Optional[UserRole] = UserRole.STUDENT

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
        if len(v) < 6:
            raise ValueError("Password minimal 6 karakter")
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
