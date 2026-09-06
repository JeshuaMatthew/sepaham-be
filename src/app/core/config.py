from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DB_URL: str
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRY_HOURS: int = 72
    BIND_ADDR: str = "0.0.0.0:8080"
    PUBLIC_BASE_URL: str = "http://localhost:8080"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
    LIVEKIT_URL: str = "ws://localhost:7880"
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "secret"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    """Returns a cached instance of settings to avoid re-reading the file on every call."""
    return Settings()

settings = get_settings()
