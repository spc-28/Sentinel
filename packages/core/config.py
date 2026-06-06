"""Application settings, loaded from environment variables and an optional .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration for every Sentinel service.

    Values are read from environment variables (case-insensitive) and, as a
    convenience for local development, from a ``.env`` file in the repo root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    environment: str = "local"
    log_level: str = "INFO"
    log_json: bool = False

    # --- API ---------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Postgres ----------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "sentinel"
    postgres_password: str = "sentinel"
    postgres_db: str = "sentinel"

    # --- Redis -------------------------------------------------------------
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # --- Qdrant ------------------------------------------------------------
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # --- Integrations ------------------------------------------------------
    github_token: str | None = None  # if set, deploys tool hits the real GitHub API

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_dsn(self) -> str:
        # asyncpg driver for SQLAlchemy's async engine
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached :class:`Settings` instance."""
    return Settings()
