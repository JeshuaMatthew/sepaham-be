from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DB_URL: str
    # Wajib diisi. Tidak ada default: kalau `.env` lupa, aplikasi gagal start
    # lebih baik daripada diam-diam menandatangani JWT dengan secret publik.
    JWT_SECRET: str
    JWT_EXPIRY_HOURS: int = 72
    BIND_ADDR: str = "0.0.0.0:8080"
    PUBLIC_BASE_URL: str = "http://localhost:8080"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
    LIVEKIT_URL: str = "ws://localhost:7880"
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    # Client ID OAuth Google. Dipakai untuk mengecek `aud` saat memverifikasi
    # ID token. Tanpa ini verifikasi ID token ditolak; login lewat OAuth
    # access token tetap jalan karena Google yang memvalidasi tokennya.
    GOOGLE_CLIENT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    """Returns a cached instance of settings to avoid re-reading the file on every call."""
    return Settings()

settings = get_settings()
