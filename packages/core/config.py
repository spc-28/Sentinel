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
    llm_model: str = "anthropic/claude-haiku-4-5"  # LiteLLM model id; override via env
    agent_max_steps: int = 15

    # --- Alert correlation -------------------------------------------------
    correlation_window_minutes: int = 5
    semantic_correlation_enabled: bool = False  # needs sentence-transformers installed
    semantic_similarity_threshold: float = 0.6

    # --- RAG ---------------------------------------------------------------
    nli_support_threshold: float = 0.5  # entailment prob above which a claim is "supported"
    log_index_window_days: int = 7  # rolling window for embedded logs

    # --- AI-pipeline detectors ---------------------------------------------
    drift_wasserstein_threshold: float = 0.05
    rag_quality_threshold: float = 0.5
    cost_spike_ratio: float = 2.5

    # --- Memory (learning from past incidents) -----------------------------
    memory_default_weight: float = 1.0  # trust a fresh memory until feedback says otherwise
    memory_semantic_threshold: float = 0.6  # min similarity to be a recall candidate
    memory_strong_match_threshold: float = 0.82  # score above which we start from the known cause
    memory_merge_similarity: float = 0.85  # min similarity to cluster two memories into a pattern
    memory_merge_min_cluster: int = 2  # distinct memories (or recurrences) needed to form a pattern
    memory_merge_seconds: int = 21600  # background pattern-merge interval (6h)

    # --- MCP (Sentinel server) ---------------------------------------------
    sentinel_api_url: str = "http://localhost:8000"  # internal API the MCP server forwards to
    mcp_api_key: str = "sentinel-dev-key"  # clients must send this in X-Sentinel-Key
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765

    # --- Observability (Langfuse) ------------------------------------------
    # Tracing is enabled only when both keys are set; cost tracking always runs.
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3000"

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
