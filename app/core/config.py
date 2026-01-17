"""Application configuration settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Meowart API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meowart"

    # Session / Cookie
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_DOMAIN: str = ".meowart.ai"
    SESSION_COOKIE_SECURE: bool = True  # Set to False for local development without HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_MAX_AGE: int = 86400 * 7  # 7 days in seconds

    # CORS
    FRONTEND_URL: str = "https://meowart.ai"
    BACKEND_URL: str = "https://api.meowart.ai"

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "https://api.meowart.ai/api/auth/google/callback"

    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "jesse.li@meowart.ai"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 5
    VERIFICATION_CODE_RATE_LIMIT_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
