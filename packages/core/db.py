"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from packages.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(_settings.sqlalchemy_dsn, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_engine() -> None:
    """Close all pooled connections; call on application shutdown."""
    await engine.dispose()
