"""
Application settings loaded from environment variables.

Pydantic-Settings validates and coerces every variable at startup so the
application fails fast with a clear error message rather than crashing later
with a confusing ``KeyError``.

Usage::

    from src.core.config import settings
    print(settings.DATABASE_URL)
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    BCRYPT_ROUNDS,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


class Settings(BaseSettings):
    """
    Centralised configuration backed by environment variables.

    All variables can be set via a ``.env`` file in the project root or
    injected directly into the process environment (e.g., Docker secrets).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "NexusCRM API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:3000"]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/nexuscrm"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Replace the plain ``postgresql://`` scheme with the async driver."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ------------------------------------------------------------------
    # Auth / JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-use-a-long-random-string",
        min_length=32,
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = REFRESH_TOKEN_EXPIRE_DAYS
    BCRYPT_ROUNDS: int = BCRYPT_ROUNDS

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached singleton of the application settings.

    The ``lru_cache`` decorator ensures the ``.env`` file is read only once,
    making this safe to call from anywhere without performance concerns.
    """
    return Settings()


settings: Settings = get_settings()
