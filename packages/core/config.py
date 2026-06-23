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

    # --- Neo4j (service dependency graph) ----------------------------------
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentinelpass"

    # --- Integrations ------------------------------------------------------
    github_token: str | None = None  # if set, deploys tool hits the real GitHub API

    # --- LLM / agents ------------------------------------------------------
    anthropic_api_key: str | None = None
    llm_model: str = "anthropic/claude-sonnet-4-6"  # LiteLLM model id; override via env
    agent_max_steps: int = 15

    # --- Alert correlation -------------------------------------------------
    correlation_window_minutes: int = 5
    semantic_correlation_enabled: bool = False  # needs sentence-transformers installed
    semantic_similarity_threshold: float = 0.6

    # --- RAG ---------------------------------------------------------------
    nli_support_threshold: float = 0.5  # entailment prob above which a claim is "supported"
    log_index_window_days: int = 7  # rolling window for embedded logs

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
